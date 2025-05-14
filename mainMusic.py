import discord
from discord.ext import commands
import wavelink
import random
from playlist_data import playlist  # Import playlist

TOKEN = 'YOUR_BOT_TOKEN'  # Replace with your bot token

bot = commands.Bot(command_prefix='!', intents=discord.Intents.all())

queue = []
looping = False

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}!')
    await wavelink.NodePool.create_node(
        bot=bot,
        host='localhost',
        port=2333,
        password='youshallnotpass'
    )

@bot.command()
async def join(ctx):
    if not ctx.author.voice:
        await ctx.send("❌ You must be in a voice channel.")
        return
    if ctx.voice_client:
        await ctx.send("I'm already in a channel.")
        return
    vc = await ctx.author.voice.channel.connect(cls=wavelink.Player)
    await vc.set_volume(0)
    await ctx.send(f"✅ Joined {ctx.author.voice.channel} (muted)")

@bot.command()
async def leave(ctx):
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
        queue.clear()
        await ctx.send("✅ Left the voice channel and cleared queue.")
    else:
        await ctx.send("❌ I'm not in a voice channel.")

@bot.command(name='playlist')
async def playlist_command(ctx):
    songs = '\n'.join(f"- {song}" for song in playlist)
    await ctx.send(f"🎶 Approved Playlist:\n{songs}")

@bot.command()
async def shuffle(ctx):
    if not ctx.voice_client:
        await ctx.invoke(join)
    song = random.choice(playlist)
    await play_song(ctx, song)

@bot.command()
async def play(ctx, *, song_name: str):
    matches = [s for s in playlist if song_name.lower() in s.lower()]
    if not matches:
        await ctx.send("❌ Song not in approved playlist.")
        return
    if not ctx.voice_client:
        await ctx.invoke(join)
    await play_song(ctx, matches[0])

@bot.command(name='queue')
async def queue_command(ctx, *, song_name: str):
    matches = [s for s in playlist if song_name.lower() in s.lower()]
    if not matches:
        await ctx.send("❌ Song not in approved playlist.")
        return
    queue.append(matches[0])
    await ctx.send(f"✅ Queued: {matches[0]}")
    if not ctx.voice_client.is_playing():
        await play_next(ctx)

@bot.command()
async def skip(ctx):
    if ctx.voice_client and ctx.voice_client.is_playing():
        await ctx.voice_client.stop()
        await ctx.send("⏭ Skipped.")
    else:
        await ctx.send("❌ Nothing is playing.")

@bot.command()
async def pause(ctx):
    if ctx.voice_client and ctx.voice_client.is_playing():
        await ctx.voice_client.pause()
        await ctx.send("⏸ Paused.")
    else:
        await ctx.send("❌ Nothing is playing.")

@bot.command()
async def resume(ctx):
    if ctx.voice_client and ctx.voice_client.is_paused():
        await ctx.voice_client.resume()
        await ctx.send("▶ Resumed.")
    else:
        await ctx.send("❌ Nothing is paused.")

@bot.command()
async def stop(ctx):
    if ctx.voice_client:
        await ctx.voice_client.stop()
        queue.clear()
        await ctx.send("⏹ Stopped playback and cleared queue.")
    else:
        await ctx.send("❌ I'm not in a voice channel.")

@bot.command()
async def loop(ctx):
    global looping
    looping = not looping
    await ctx.send(f"🔁 Looping is now {'enabled' if looping else 'disabled'}.")

@bot.command()
async def np(ctx):
    if ctx.voice_client and ctx.voice_client.is_playing():
        current = ctx.voice_client.current
        await ctx.send(f"🎵 Now playing: {current.title}")
    else:
        await ctx.send("❌ Nothing is playing.")

@bot.command()
async def mute(ctx):
    if ctx.voice_client:
        await ctx.voice_client.set_volume(0)
        await ctx.send("🔇 Bot muted.")
    else:
        await ctx.send("❌ I'm not in a voice channel.")

@bot.command()
async def unmute(ctx):
    if ctx.voice_client:
        await ctx.voice_client.set_volume(100)
        await ctx.send("🔊 Bot unmuted.")
    else:
        await ctx.send("❌ I'm not in a voice channel.")

@bot.command()
async def volume(ctx, level: int):
    if ctx.voice_client:
        if 0 <= level <= 100:
            await ctx.voice_client.set_volume(level)
            await ctx.send(f"🔊 Volume set to {level}%.")
        else:
            await ctx.send("❌ Volume must be between 0 and 100.")
    else:
        await ctx.send("❌ I'm not in a voice channel.")

@bot.command(name='help')
async def help_command(ctx):
    commands_list = """
🎧 **Ultimate Music Bot Commands**
- !join → Join your VC (muted by default)
- !leave → Leave VC and clear queue
- !playlist → Show approved playlist
- !shuffle → Play random song from playlist
- !play <song> → Play specific approved song
- !queue <song> → Queue specific approved song
- !skip → Skip current song
- !pause → Pause playback
- !resume → Resume playback
- !stop → Stop playback and clear queue
- !loop → Toggle loop mode
- !np → Show currently playing song
- !mute → Mute bot (volume 0)
- !unmute → Unmute bot (volume 100)
- !volume <0-100> → Set volume manually
"""
    await ctx.send(commands_list)

async def play_next(ctx):
    if looping and ctx.voice_client.current:
        await ctx.voice_client.play(ctx.voice_client.current)
        await ctx.send(f"🔁 Looping: {ctx.voice_client.current.title}")
        return
    if queue:
        song_name = queue.pop(0)
        await play_song(ctx, song_name)
    else:
        await ctx.send("📃 Queue is empty.")

async def play_song(ctx, song_name):
    query = f'ytsearch:{song_name}'
    tracks = await wavelink.YouTubeTrack.search(query=query)
    if not tracks:
        await ctx.send("❌ Could not find the song on YouTube.")
        return
    track = tracks[0]
    await ctx.voice_client.set_volume(100)
    await ctx.voice_client.play(track)
    await ctx.send(f"🎶 Now playing: {track.title}")

    @ctx.voice_client.on('end')
    async def _on_end(_, __):
        await play_next(ctx)

bot.run(TOKEN)
