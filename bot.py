import json
import os
import io
import graphviz
from PIL import Image
from graphviz import Digraph
from discord import Member, File
from discord.ext.commands import Bot, UserConverter

data = {}
bot = Bot(command_prefix='!')

class BotErr(Exception):
	def __init__(self, msg):
		self.msg = msg

	def __str__(self):
		return self.msg

def save():
	open('savedData.json', 'w').write(json.dumps(data, indent=4))

def load():
	global data
	data = json.loads(open('savedData.json', 'r').read())

def check_ctx(ctx):
	author = ctx.message.author
	if type(author) is not Member:
		raise Exception('PMs are not allowed.')
	if 'Bot commander' not in map(lambda x: x.name, ctx.message.author.roles):
		raise BotErr('"Bot commander" role required.')

@bot.command()
async def mute(ctx, muter: UserConverter, muted: UserConverter):
	try:
		check_ctx(ctx)
		guild_id = str(ctx.guild.id)
		muter_id = str(muter.id)
		muted_id = str(muted.id)
		if guild_id not in data:
			data[guild_id] = {}
		if muter_id not in data[guild_id]:
			data[guild_id][muter_id] = [muted_id]
		elif muted_id not in data[guild_id][muter_id]:
			data[guild_id][muter_id].append(muted_id)
		save()
	except BotErr as e:
		await ctx.send(e)

@bot.command()
async def unmute(ctx, muter: UserConverter, muted: UserConverter):
	try:
		check_ctx(ctx)
		guild_id = str(ctx.guild.id)
		muter_id = str(muter.id)
		muted_id = str(muted.id)
		if guild_id not in data:
			return
		if muter_id not in data[guild_id]:
			return
		if muted_id in data[guild_id][muter_id]:
			data[guild_id][muter_id].remove(muted_id)
		save()
	except BotErr as e:
		await ctx.send(e)

def round_img(img):
	width, height = img.size
	r = width / 2.0
	for x in range(width):
		for y in range(height):
			if (x - r) ** 2 + (y - r) ** 2 < r ** 2:
				continue
			img.putpixel((x, y), (255, 255, 255, 0))
	return img

async def cached_img(id, asset):
	if id is None:
		id = '0'

	if not os.path.exists('cache'):
		os.mkdir('cache')
	
	cached_file = os.path.join('cache', id + '.png')
	if os.path.isfile(cached_file):
		return cached_file

	raw = await asset.read()
	img = round_img(Image.open(io.BytesIO(raw)))
	img.save(cached_file)
	return cached_file

async def draw(output, guild_id, engine='circo'):
	if guild_id not in data:
		return

	uids = sorted(list(set(sum(list(map(lambda kv: [kv[0]] + kv[1], data[guild_id].items())), []))))
	guild = bot.get_guild(int(guild_id))
	members = [guild.get_member(int(x)) for x in uids]
	g = Digraph('G', filename='graph.gv', engine=engine)
	for m in members:
		g.node(str(m.id), '', {
			'fontname': 'whitney',
			'fontsize': '22',
			'shape': 'circle',
			'xlabel': m.display_name,
			'image': await cached_img(m.avatar, m.avatar_url_as(format='png', size=64)),
			'imagescale': 'true',
			'style': 'filled',
			'fixedsize': 'true',
			'forcelabels': 'true',
			'color': 'white',
		})
	for (muter, muted) in data[guild_id].items():
		for u in muted:
			g.edge(muter, u, None, {
				'color': 'red',
				'penwidth': '2',
			})

	g.render(output, format='png')
	os.remove(output) # graph file

@bot.command()
async def show(ctx):
	try:
		check_ctx(ctx)
		await draw('graph', str(ctx.guild.id))
		await ctx.send(file=File('graph.png'))
		os.remove('graph.png')
	except BotErr as e:
		await ctx.send(e)

if __name__ == '__main__':
	try:
		load()
	except Exception as e:
		print(str(e))
	bot.run(open('discord_token.txt').read())