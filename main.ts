import { App, Modal, Notice, Plugin, PluginSettingTab, Setting } from 'obsidian';
import { spawn, ChildProcess } from 'child_process';
import { join } from 'path';

interface ObsidianToEpubSettings {
	serverPort: number;
	pythonPath: string;
	autoOpenBrowser: boolean;
}

const DEFAULT_SETTINGS: ObsidianToEpubSettings = {
	serverPort: 5002,
	pythonPath: 'python',
	autoOpenBrowser: true
}

export default class ObsidianToEpubPlugin extends Plugin {
	settings: ObsidianToEpubSettings;
	serverProcess: ChildProcess | null = null;
	serverRunning = false;

	async onload() {
		await this.loadSettings();

		// Добавляем команду в палитру команд
		this.addCommand({
			id: 'open-epub-converter',
			name: 'Открыть конвертер EPUB',
			callback: () => {
				this.openConverter();
			}
		});

		// Добавляем иконку в ribbon
		const ribbonIconEl = this.addRibbonIcon('book', 'EPUB Converter', (evt: MouseEvent) => {
			this.openConverter();
		});

		// Добавляем настройки плагина
		this.addSettingTab(new ObsidianToEpubSettingTab(this.app, this));

		console.log('Obsidian to EPUB plugin loaded');
	}

	onunload() {
		this.stopServer();
		console.log('Obsidian to EPUB plugin unloaded');
	}

	async loadSettings() {
		this.settings = Object.assign({}, DEFAULT_SETTINGS, await this.loadData());
	}

	async saveSettings() {
		await this.saveData(this.settings);
	}

	async openConverter() {
		try {
			// Запускаем сервер если не запущен
			if (!this.serverRunning) {
				await this.startServer();
			}

			// Получаем путь к текущему vault
			const vaultPath = (this.app.vault.adapter as any).basePath;
			
			// Отправляем путь vault на сервер
			await this.setVaultPath(vaultPath);

			// Открываем браузер
			if (this.settings.autoOpenBrowser) {
				this.openBrowser();
			}

			new Notice('EPUB конвертер открыт в браузере');
		} catch (error) {
			new Notice(`Ошибка: ${error.message}`);
			console.error('Error opening converter:', error);
		}
	}

	async startServer(): Promise<void> {
		return new Promise((resolve, reject) => {
			try {
				// Путь к скрипту сервера относительно плагина
				const serverScript = join(__dirname, 'server', 'app.py');
				
				// Запускаем Python сервер
				this.serverProcess = spawn(this.settings.pythonPath, [serverScript], {
					cwd: join(__dirname, 'server'),
					env: { ...process.env, PYTHONPATH: join(__dirname, 'server') }
				});

				this.serverProcess.stdout?.on('data', (data) => {
					console.log(`Server output: ${data}`);
					if (data.toString().includes('Running on')) {
						this.serverRunning = true;
						resolve();
					}
				});

				this.serverProcess.stderr?.on('data', (data) => {
					console.error(`Server error: ${data}`);
				});

				this.serverProcess.on('close', (code) => {
					console.log(`Server process exited with code ${code}`);
					this.serverRunning = false;
					this.serverProcess = null;
				});

				// Таймаут для запуска сервера
				setTimeout(() => {
					if (!this.serverRunning) {
						reject(new Error('Сервер не запустился в течение 10 секунд'));
					}
				}, 10000);

			} catch (error) {
				reject(error);
			}
		});
	}

	stopServer() {
		if (this.serverProcess) {
			this.serverProcess.kill();
			this.serverProcess = null;
			this.serverRunning = false;
		}
	}

	async setVaultPath(vaultPath: string) {
		try {
			const response = await fetch(`http://localhost:${this.settings.serverPort}/api/set-project`, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ 
					path: vaultPath,
					name: this.app.vault.getName()
				})
			});
			
			if (!response.ok) {
				throw new Error('Не удалось установить путь к vault');
			}
		} catch (error) {
			console.error('Error setting vault path:', error);
			throw error;
		}
	}

	openBrowser() {
		const url = `http://localhost:${this.settings.serverPort}`;
		
		// Открываем браузер в зависимости от платформы
		const { exec } = require('child_process');
		let command: string;

		if (process.platform === 'darwin') {
			command = `open "${url}"`;
		} else if (process.platform === 'win32') {
			command = `start "${url}"`;
		} else {
			command = `xdg-open "${url}"`;
		}

		exec(command, (error: any) => {
			if (error) {
				console.error('Error opening browser:', error);
				new Notice(`Откройте браузер и перейдите по адресу: ${url}`);
			}
		});
	}
}

class ObsidianToEpubSettingTab extends PluginSettingTab {
	plugin: ObsidianToEpubPlugin;

	constructor(app: App, plugin: ObsidianToEpubPlugin) {
		super(app, plugin);
		this.plugin = plugin;
	}

	display(): void {
		const {containerEl} = this;

		containerEl.empty();

		containerEl.createEl('h2', {text: 'Настройки Obsidian to EPUB'});

		new Setting(containerEl)
			.setName('Порт сервера')
			.setDesc('Порт для запуска веб-сервера')
			.addText(text => text
				.setPlaceholder('5002')
				.setValue(this.plugin.settings.serverPort.toString())
				.onChange(async (value) => {
					this.plugin.settings.serverPort = parseInt(value) || 5002;
					await this.plugin.saveSettings();
				}));

		new Setting(containerEl)
			.setName('Путь к Python')
			.setDesc('Команда для запуска Python (python, python3, или полный путь)')
			.addText(text => text
				.setPlaceholder('python')
				.setValue(this.plugin.settings.pythonPath)
				.onChange(async (value) => {
					this.plugin.settings.pythonPath = value;
					await this.plugin.saveSettings();
				}));

		new Setting(containerEl)
			.setName('Автоматически открывать браузер')
			.setDesc('Открывать браузер при запуске конвертера')
			.addToggle(toggle => toggle
				.setValue(this.plugin.settings.autoOpenBrowser)
				.onChange(async (value) => {
					this.plugin.settings.autoOpenBrowser = value;
					await this.plugin.saveSettings();
				}));

		new Setting(containerEl)
			.setName('Статус сервера')
			.setDesc(this.plugin.serverRunning ? 'Сервер запущен' : 'Сервер остановлен')
			.addButton(button => button
				.setButtonText(this.plugin.serverRunning ? 'Остановить' : 'Запустить')
				.onClick(async () => {
					if (this.plugin.serverRunning) {
						this.plugin.stopServer();
						new Notice('Сервер остановлен');
					} else {
						try {
							await this.plugin.startServer();
							new Notice('Сервер запущен');
						} catch (error) {
							new Notice(`Ошибка запуска сервера: ${error.message}`);
						}
					}
					this.display(); // Обновляем интерфейс
				}));
	}
} 