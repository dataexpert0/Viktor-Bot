import os
import asyncio
import discord
from discord.ext import commands
from dotenv import load_dotenv

# Base
load_dotenv()
TOKEN = os.getenv('discord_token')

intents = discord.Intents.default()
intents.message_content = True 

bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    print(f'Bot conectado como {bot.user.name} (ID: {bot.user.id})')

# Inicialização dos componentes
async def main():
    for filename in os.listdir('./cogs'):
        if filename.endswith('.py'):
            try:
                await bot.load_extension(f'cogs.{filename[:-3]}')
                print(f'Componente {filename} carregado com sucesso.')
            except Exception as e:
                print(f'Falha ao carregar o componente {filename}.')
                print(f'Debug: {e}')

    await bot.start(TOKEN)

if __name__ == '__main__':
    asyncio.run(main())