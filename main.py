import os
import asyncio
import discord
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv('discord_token')

class MyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        
        super().__init__(command_prefix='!', intents=intents)

    async def setup_hook(self):
        print("Carregando componentes (cogs)...")
        for filename in os.listdir('./cogs'):
            if filename.endswith('.py'):
                try:
                    await self.load_extension(f'cogs.{filename[:-3]}')
                    print(f'✅ Componente {filename} carregado com sucesso.')
                except Exception as e:
                    print(f'❌ Falha ao carregar o componente {filename}.')
                    print(f'[ERRO] {e}')
        
        try:
            print("Sincronizando comandos com o Discord...")
            synced = await self.tree.sync()
            if synced:
                print(f"✅ Comandos Slash sincronizados: {[cmd.name for cmd in synced]}")
            else:
                print("✅ Nenhum comando novo para sincronizar.")
        except Exception as e:
            print(f"❌ Erro ao sincronizar slash commands: {e}")

    async def on_ready(self):
        print(f'Logado como {self.user}!')


async def main():
    bot = MyBot()
    await bot.start(TOKEN)

if __name__ == '__main__':
    asyncio.run(main())