import discord
from discord.ext import commands
import json
import os
import time
import random
import asyncio

# =====================
# INTENTS
# =====================
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)
bot.remove_command("help")

# =====================
# PLIKI
# =====================
DATA_FILE = "users.json"
COOLDOWN_FILE = "cooldowns.json"
DAILY_FILE = "daily.json"

# =====================
# STAŁE
# =====================
SHOP_ITEMS = {
    "burger": 100,
    "czerwony": 500,
    "niebieski": 500,
    "zielony": 500,
    "zolty": 500,
    "fioletowy": 500,
    "rozowy": 500
}

COLOR_ROLES = {
    "czerwony": "CZERWONY",
    "niebieski": "NIEBIESKI",
    "zielony": "ZIELONY",
    "zolty": "ZOLTY",
    "fioletowy": "FIOLETOWY",
    "rozowy": "ROZOWY"
}

ROLE_COLOR_EMOJIS = {
    "czerwony": "❤️",
    "niebieski": "💙",
    "zielony": "💚",
    "zolty": "💛",
    "fioletowy": "💜",
    "rozowy": "🩷"
}

BET_COLORS = {
    "czarny": {"emoji": "⚫", "multiplier": 2},
    "czerwony": {"emoji": "🔴", "multiplier": 2},
    "zielony": {"emoji": "🟢", "multiplier": 14}
}

PROFESSIONS = {
    "SĘDZIA": 500,
    "PSYCHOLOG": 400,
    "ADWOKAT": 250
}

PROFESSION_EMOJIS = {
    "SĘDZIA": "⚖️",
    "PSYCHOLOG": "🧠",
    "ADWOKAT": "📋",
    "Pracownik": "💼"
}

# Jedna aktywna gra jackpot na kanał
ACTIVE_JACKPOTS = {}

# Wiele battle naraz
ACTIVE_BATTLES = {}
ACTIVE_BATTLE_USERS = set()

# =====================
# LOAD / SAVE
# =====================
def load(path, default):
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return default
    return default


users = load(DATA_FILE, {})
cooldowns = load(COOLDOWN_FILE, {})
daily_data = load(DAILY_FILE, {})


def save():
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, ensure_ascii=False, indent=4)


def save_cd():
    with open(COOLDOWN_FILE, "w", encoding="utf-8") as f:
        json.dump(cooldowns, f, ensure_ascii=False, indent=4)


def save_daily():
    with open(DAILY_FILE, "w", encoding="utf-8") as f:
        json.dump(daily_data, f, ensure_ascii=False, indent=4)


# =====================
# HELPERY
# =====================
def get_user(user_id):
    user_id = str(user_id)

    if user_id not in users:
        users[user_id] = {"money": 0, "inv": {}, "color": None}

    if not isinstance(users[user_id].get("inv"), dict):
        users[user_id]["inv"] = {}

    if "color" not in users[user_id]:
        users[user_id]["color"] = None

    if "money" not in users[user_id]:
        users[user_id]["money"] = 0

    return users[user_id]


def set_embed_thumbnail(embed, user):
    if user and getattr(user, "avatar", None):
        embed.set_thumbnail(url=user.avatar.url)


def format_money(amount):
    return f"{int(amount):,}$".replace(",", " ")


def get_bet_result(selected_color):
    roll = random.uniform(0, 100)

    if selected_color == "czerwony":
        if roll < 40:
            return "czerwony"
        if roll < 42.5:
            return "zielony"
        return "czarny"

    if selected_color == "czarny":
        if roll < 40:
            return "czarny"
        if roll < 42.5:
            return "zielony"
        return "czerwony"

    if roll < 2.5:
        return "zielony"
    if roll < 51.25:
        return "czerwony"
    return "czarny"


def cleanup_battle(message_id):
    battle = ACTIVE_BATTLES.pop(message_id, None)
    if not battle:
        return

    ACTIVE_BATTLE_USERS.discard(battle["author_id"])
    ACTIVE_BATTLE_USERS.discard(battle["enemy_id"])


# =====================
# READY
# =====================
@bot.event
async def on_ready():
    print(f"✅ Bot działa jako {bot.user}")


# =====================
# KOMENDY / HELP
# =====================
@bot.command(aliases=["help"])
async def komendy(ctx):
    embed = discord.Embed(
        title="🎰 NEON CASINO PANEL",
        description=(
            "Tutaj masz wszystkie komendy bota.\n"
            "Argumenty w `()` są wymagane, a w `[]` opcjonalne."
        ),
        color=0x11131A
    )

    embed.add_field(
        name="💰 EKONOMIA",
        value=(
            "`!balance [@osoba]` - sprawdza stan konta\n"
            "`!work` - pracujesz i zarabiasz co 1h\n"
            "`!daily` - odbierasz nagrodę co 24h\n"
            "`!pay @osoba kwota` - wysyłasz komuś pieniądze"
        ),
        inline=False
    )

    embed.add_field(
        name="🎲 GRY SOLO",
        value=(
            "`!bet (czarny/czerwony/zielony) (kwota)` - ruletka\n"
            "`!slot (kwota)` - automaty\n"
            "`!blackjack (kwota)` - blackjack\n"
            "`!bj (kwota)` - skrót do blackjacka"
        ),
        inline=False
    )

    embed.add_field(
        name="⚔️ GRY DLA WIELU OSÓB",
        value=(
            "`!battle @osoba kwota` - pojedynek 1v1 o pieniądze\n"
            "`!jackpot kwota` - tworzysz jackpot\n"
            "`!joinpot kwota` - dołączasz do jackpota"
        ),
        inline=False
    )

    embed.add_field(
        name="🛒 SKLEP",
        value=(
            "`!sklep` - pokazuje sklep\n"
            "`!kup item ilość` - kupujesz przedmiot\n"
            "`!eq` - pokazuje ekwipunek"
        ),
        inline=False
    )

    embed.add_field(
        name="👑 ADMIN",
        value=(
            "`!addmoney @osoba kwota` - dodaje pieniądze\n"
            "`!setmoney @osoba kwota` - ustawia pieniądze"
        ),
        inline=False
    )

    embed.add_field(
        name="📘 INSTRUKCJE",
        value=(
            "`!battle` - wyzwany gracz akceptuje reakcją `✅`\n"
            "`!blackjack` - `✋` dobiera kartę, `🛑` kończy turę\n"
            "`!jackpot` - inni gracze wchodzą przez `!joinpot`\n"
            "`!bet` - kolory to `czarny`, `czerwony`, `zielony`\n"
            "`!help` działa tak samo jak `!komendy`"
        ),
        inline=False
    )

    embed.set_footer(text="Neon Casino • High stakes • Good luck")
    set_embed_thumbnail(embed, ctx.bot.user)
    await ctx.send(embed=embed)


# =====================
# BALANCE
# =====================
@bot.command()
async def balance(ctx, member: discord.Member = None):
    if member is None:
        member = ctx.author

    data = get_user(member.id)

    embed = discord.Embed(
        title="💰 BALANCE",
        description=member.mention,
        color=0xFFD700
    )
    embed.add_field(name="Pieniądze", value=f"**{format_money(data['money'])}**", inline=False)
    set_embed_thumbnail(embed, member)

    await ctx.send(embed=embed)


# =====================
# WORK
# =====================
@bot.command()
async def work(ctx):
    user_id = str(ctx.author.id)
    now = time.time()
    is_owner = await bot.is_owner(ctx.author)

    if not is_owner and user_id in cooldowns:
        left = int(3600 - (now - float(cooldowns[user_id])))
        if left > 0:
            embed = discord.Embed(
                title="⏳ CZEKAJ!",
                description=f"Wróć za {left // 60}m {left % 60}s",
                color=0xFF6B6B
            )
            return await ctx.send(embed=embed)

    if not is_owner:
        cooldowns[user_id] = now
        save_cd()

    earnings = 200
    profession = "Pracownik"

    for prof_name, prof_earnings in PROFESSIONS.items():
        role = discord.utils.get(ctx.guild.roles, name=prof_name)
        if role and role in ctx.author.roles:
            earnings = prof_earnings
            profession = prof_name
            break

    emoji = PROFESSION_EMOJIS.get(profession, "💼")

    data = get_user(user_id)
    data["money"] += earnings
    save()

    embed = discord.Embed(
        title="💪 PRACA",
        description=f"{emoji} {profession}\n+**{format_money(earnings)}**",
        color=0x51CF66
    )
    set_embed_thumbnail(embed, ctx.author)
    await ctx.send(embed=embed)


# =====================
# DAILY
# =====================
@bot.command()
async def daily(ctx):
    user_id = str(ctx.author.id)
    now = time.time()

    if user_id in daily_data:
        left = int(86400 - (now - float(daily_data[user_id])))
        if left > 0:
            hours = left // 3600
            minutes = (left % 3600) // 60
            embed = discord.Embed(
                title="⏳ JUŻ BRAŁEŚ!",
                description=f"Wróć za {hours}h {minutes}m",
                color=0xFF6B6B
            )
            return await ctx.send(embed=embed)

    reward = random.randint(500, 1200)
    data = get_user(user_id)
    data["money"] += reward
    daily_data[user_id] = now

    save()
    save_daily()

    embed = discord.Embed(
        title="🎁 DAILY!",
        description=f"Otrzymałeś **{format_money(reward)}**",
        color=0xFFD700
    )
    set_embed_thumbnail(embed, ctx.author)
    await ctx.send(embed=embed)


# =====================
# PAY
# =====================
@bot.command()
async def pay(ctx, member: discord.Member, amount: int):
    if member.bot:
        return await ctx.send("❌ Nie możesz wysyłać pieniędzy botowi.")

    if member.id == ctx.author.id:
        return await ctx.send("❌ Nie możesz wysłać pieniędzy samemu sobie.")

    if amount <= 0:
        return await ctx.send("❌ Kwota musi być większa niż 0")

    sender_data = get_user(ctx.author.id)

    if sender_data["money"] < amount:
        return await ctx.send(f"❌ Masz tylko **{format_money(sender_data['money'])}**")

    receiver_data = get_user(member.id)

    sender_data["money"] -= amount
    receiver_data["money"] += amount
    save()

    embed = discord.Embed(
        title="💸 TRANSFER",
        description=f"{ctx.author.mention} → {member.mention}\n**{format_money(amount)}**",
        color=0x51CF66
    )
    await ctx.send(embed=embed)


# =====================
# ADDMONEY
# =====================
@bot.command()
@commands.is_owner()
async def addmoney(ctx, member: discord.Member, amount: int):
    if amount <= 0:
        return await ctx.send("❌ Kwota musi być większa niż 0")

    data = get_user(member.id)
    data["money"] += amount
    save()

    embed = discord.Embed(
        title="👑 ADMIN",
        description=f"Dodano **{format_money(amount)}** dla {member.mention}",
        color=0x9C27B0
    )
    embed.add_field(name="Nowa kasa", value=f"**{format_money(data['money'])}**")
    set_embed_thumbnail(embed, member)
    await ctx.send(embed=embed)


# =====================
# SETMONEY
# =====================
@bot.command()
@commands.is_owner()
async def setmoney(ctx, member: discord.Member, amount: int):
    if amount < 0:
        return await ctx.send("❌ Kwota nie może być ujemna")

    data = get_user(member.id)
    data["money"] = amount
    save()

    embed = discord.Embed(
        title="💰 USTAWIONO KASĘ",
        description=f"{member.mention} ma teraz **{format_money(amount)}**",
        color=0x00C853
    )
    set_embed_thumbnail(embed, member)
    await ctx.send(embed=embed)


# =====================
# BET
# =====================
import random

def get_bet_result(bet_color):
    if bet_color == "czerwony":
        return random.choices(
            ["czerwony", "czarny", "zielony"],
            weights=[30, 67.5, 2.5]
        )[0]

    elif bet_color == "czarny":
        return random.choices(
            ["czarny", "czerwony", "zielony"],
            weights=[30, 67.5, 2.5]
        )[0]

    elif bet_color == "zielony":
        return random.choices(
            ["zielony", "czarny", "czerwony"],
            weights=[2.5, 48.75, 48.75]
        )[0]


@bot.command()
@commands.cooldown(1, 2, commands.BucketType.user)
async def bet(ctx, color, amount: int):
    color = color.lower()

    if color not in BET_COLORS:
        return await ctx.send("❌ Użyj: `!bet (czarny/czerwony/zielony) (kwota)`")

    if amount <= 0:
        return await ctx.send("❌ Kwota musi być większa niż 0.")

    data = get_user(ctx.author.id)

    if data["money"] < amount:
        return await ctx.send(f"❌ Masz tylko **{format_money(data['money'])}**")

    data["money"] -= amount
    save()

    neon_gold = 0xF5C542
    neon_red = 0xFF4D6D
    neon_green = 0x57F287
    dark_casino = 0x11131A

    spin_frames = [
        "✦ ⚫ 🔴 🟢 ⚫ 🔴 ✦",
        "✦ 🔴 ⚫ 🔴 🟢 ⚫ ✦",
        "✦ 🟢 ⚫ 🔴 ⚫ 🔴 ✦",
        "✦ ⚫ 🔴 ⚫ 🔴 🟢 ✦",
        "✦ 🔴 🟢 ⚫ 🔴 ⚫ ✦"
    ]

    start_embed = discord.Embed(
        title="🎰 NEON CASINO",
        description=(
            f"╔══════════════╗\n"
            f"**Gracz:** {ctx.author.mention}\n"
            f"**Zakład:** {BET_COLORS[color]['emoji']} **{color.capitalize()}**\n"
            f"**Stawka:** **{format_money(amount)}**\n"
            f"╚══════════════╝"
        ),
        color=dark_casino
    )
    start_embed.add_field(name="Status", value="`Rozpoczynam losowanie...`", inline=False)
    start_embed.set_footer(text="Las Vegas vibes")
    set_embed_thumbnail(start_embed, ctx.author)

    msg = await ctx.send(embed=start_embed)

    delay = 1.0 / len(spin_frames)

    for i, frame in enumerate(spin_frames):
        spin_embed = discord.Embed(
            title="🎰 NEON CASINO",
            description=(
                f"╔══════════════╗\n"
                f"**Gracz:** {ctx.author.mention}\n"
                f"**Zakład:** {BET_COLORS[color]['emoji']} **{color.capitalize()}**\n"
                f"**Stawka:** **{format_money(amount)}**\n"
                f"╚══════════════╝"
            ),
            color=neon_gold if i % 2 == 0 else dark_casino
        )
        spin_embed.add_field(name="Ruletka", value=f"`{frame}`", inline=False)
        spin_embed.add_field(name="Status", value="`Kręci się...`", inline=False)
        spin_embed.set_footer(text="Neon lights • High stakes")
        set_embed_thumbnail(spin_embed, ctx.author)

        await msg.edit(embed=spin_embed)
        await asyncio.sleep(delay)

    result = get_bet_result(color)
    won = result == color

    if won:
        winnings = amount * BET_COLORS[color]["multiplier"]
        data["money"] += winnings
        save()

        final_color = neon_green if result == "zielony" else neon_gold
        final_embed = discord.Embed(
            title="🎉 NEON CASINO",
            description=(
                f"**Twój typ:** {BET_COLORS[color]['emoji']} **{color.capitalize()}**\n"
                f"**Wylosowano:** {BET_COLORS[result]['emoji']} **{result.capitalize()}**"
            ),
            color=final_color
        )
        final_embed.add_field(name="Wynik", value="`WYGRANA`", inline=True)
        final_embed.add_field(name="Nagroda", value=f"**+{format_money(winnings)}**", inline=True)
        final_embed.add_field(name="Saldo", value=f"**{format_money(data['money'])}**", inline=False)
        final_embed.set_footer(text="Casino paid out")
    else:
        final_embed = discord.Embed(
            title="💸 NEON CASINO",
            description=(
                f"**Twój typ:** {BET_COLORS[color]['emoji']} **{color.capitalize()}**\n"
                f"**Wylosowano:** {BET_COLORS[result]['emoji']} **{result.capitalize()}**"
            ),
            color=neon_red
        )
        final_embed.add_field(name="Wynik", value="`PRZEGRANA`", inline=True)
        final_embed.add_field(name="Strata", value=f"**-{format_money(amount)}**", inline=True)
        final_embed.add_field(name="Saldo", value=f"**{format_money(data['money'])}**", inline=False)
        final_embed.set_footer(text="House always watches")

    set_embed_thumbnail(final_embed, ctx.author)
    await msg.edit(embed=final_embed)


@bet.error
async def bet_error(ctx, error):
    if isinstance(error, commands.CommandOnCooldown):
        return await ctx.send(f"⏳ Następny zakład za **{error.retry_after:.1f}s**")
    if isinstance(error, commands.MissingRequiredArgument):
        return await ctx.send("❌ Użyj: `!bet (czarny/czerwony/zielony) (kwota)`")
    if isinstance(error, commands.BadArgument):
        return await ctx.send("❌ Kwota musi być liczbą, np. `!bet czerwony 500`")


# =====================
# SLOT
# =====================
@bot.command()
@commands.cooldown(1, 2, commands.BucketType.user)
async def slot(ctx, amount: int):
    if amount <= 0:
        return await ctx.send("❌ Kwota musi być większa niż 0")

    data = get_user(ctx.author.id)

    if data["money"] < amount:
        return await ctx.send(f"❌ Masz tylko **{format_money(data['money'])}**")

    data["money"] -= amount
    save()

    neon_gold = 0xF5C542
    neon_red = 0xFF4D6D
    neon_green = 0x57F287
    dark_casino = 0x11131A

    weighted_symbols = (
        ["🍎"] * 22 +
        ["🍊"] * 20 +
        ["🍋"] * 18 +
        ["🍌"] * 16 +
        ["🍉"] * 12 +
        ["🍇"] * 8 +
        ["🍓"] * 6 +
        ["⭐"] * 4 +
        ["💎"] * 2 +
        ["💰"] * 1
    )

    def spin_symbol():
        return random.choice(weighted_symbols)

    def get_reward(reels, bet_amount):
        a, b, c = reels

        if reels == ["💰", "💰", "💰"]:
            return int(bet_amount * 20), "🏆 JACKPOT! Trzy razy 💰"
        if reels == ["💎", "💎", "💎"]:
            return int(bet_amount * 12), "💎 Mega trafienie! Trzy razy 💎"
        if reels == ["⭐", "⭐", "⭐"]:
            return int(bet_amount * 7), "🌟 Lucky hit! Trzy razy ⭐"
        if a == b == c:
            return int(bet_amount * 4), "🎉 Trzy takie same symbole!"
        if a == b or b == c or a == c:
            return int(bet_amount * 1.8), "✨ Dwie takie same!"
        return 0, "💸 Tym razem kasyno wygrywa."

    start_embed = discord.Embed(
        title="🎰 NEON CASINO",
        description=(
            f"╔══════════════╗\n"
            f"**Gracz:** {ctx.author.mention}\n"
            f"**Stawka:** **{format_money(amount)}**\n"
            f"╚══════════════╝"
        ),
        color=dark_casino
    )
    set_embed_thumbnail(start_embed, ctx.author)
    msg = await ctx.send(embed=start_embed)

    final_reels = [spin_symbol(), spin_symbol(), spin_symbol()]

    frames = [
        ["🎲", "🎲", "🎲"],
        [spin_symbol(), "🎲", "🎲"],
        [spin_symbol(), spin_symbol(), "🎲"],
        [spin_symbol(), spin_symbol(), spin_symbol()],
        [final_reels[0], spin_symbol(), spin_symbol()],
        [final_reels[0], final_reels[1], spin_symbol()],
        final_reels
    ]

    delay = 1.0 / len(frames)

    for i, frame in enumerate(frames):
        spin_embed = discord.Embed(
            title="🎰 NEON CASINO",
            description=(
                f"╔══════════════╗\n"
                f"**Gracz:** {ctx.author.mention}\n"
                f"**Stawka:** **{format_money(amount)}**\n"
                f"╚══════════════╝"
            ),
            color=neon_gold if i % 2 == 0 else dark_casino
        )
        spin_embed.add_field(
            name="Slot Machine",
            value=(
                f"`╔═══╦═══╦═══╗`\n"
                f"`║ {frame[0]} ║ {frame[1]} ║ {frame[2]} ║`\n"
                f"`╚═══╩═══╩═══╝`"
            ),
            inline=False
        )
        spin_embed.add_field(name="Status", value="`Bębny się kręcą...`", inline=False)
        spin_embed.set_footer(text="Neon lights • Lucky spin")
        set_embed_thumbnail(spin_embed, ctx.author)

        await msg.edit(embed=spin_embed)
        await asyncio.sleep(delay)

    reward, reason = get_reward(final_reels, amount)

    if reward > 0:
        data["money"] += reward
        save()

        final_color = neon_green if reward >= amount * 4 else neon_gold
        final_embed = discord.Embed(
            title="🎉 NEON CASINO",
            description=(
                f"`╔═══╦═══╦═══╗`\n"
                f"`║ {final_reels[0]} ║ {final_reels[1]} ║ {final_reels[2]} ║`\n"
                f"`╚═══╩═══╩═══╝`\n\n"
                f"{reason}"
            ),
            color=final_color
        )
        final_embed.add_field(name="Wynik", value="`WYGRANA`", inline=True)
        final_embed.add_field(name="Nagroda", value=f"**+{format_money(reward)}**", inline=True)
        final_embed.add_field(name="Saldo", value=f"**{format_money(data['money'])}**", inline=False)
        final_embed.set_footer(text="Kasyno wypłaca nagrodę")
    else:
        final_embed = discord.Embed(
            title="💸 NEON CASINO",
            description=(
                f"`╔═══╦═══╦═══╗`\n"
                f"`║ {final_reels[0]} ║ {final_reels[1]} ║ {final_reels[2]} ║`\n"
                f"`╚═══╩═══╩═══╝`\n\n"
                f"{reason}"
            ),
            color=neon_red
        )
        final_embed.add_field(name="Wynik", value="`PRZEGRANA`", inline=True)
        final_embed.add_field(name="Strata", value=f"**-{format_money(amount)}**", inline=True)
        final_embed.add_field(name="Saldo", value=f"**{format_money(data['money'])}**", inline=False)
        final_embed.set_footer(text="House always watches")

    set_embed_thumbnail(final_embed, ctx.author)
    await msg.edit(embed=final_embed)


@slot.error
async def slot_error(ctx, error):
    if isinstance(error, commands.CommandOnCooldown):
        return await ctx.send(f"⏳ Następny spin za **{error.retry_after:.1f}s**")
    if isinstance(error, commands.MissingRequiredArgument):
        return await ctx.send("❌ Użyj: `!slot (kwota)`")
    if isinstance(error, commands.BadArgument):
        return await ctx.send("❌ Kwota musi być liczbą, np. `!slot 500`")


# =====================
# BATTLE
# =====================
@bot.command()
@commands.cooldown(1, 4, commands.BucketType.user)
async def battle(ctx, member: discord.Member, amount: int):
    if member.bot:
        return await ctx.send("❌ Nie możesz wyzwać bota.")

    if member.id == ctx.author.id:
        return await ctx.send("❌ Nie możesz wyzwać samego siebie.")

    if amount <= 0:
        return await ctx.send("❌ Kwota musi być większa niż 0.")

    if ctx.author.id in ACTIVE_BATTLE_USERS:
        return await ctx.send("❌ Jesteś już w trakcie innego battle.")

    if member.id in ACTIVE_BATTLE_USERS:
        return await ctx.send("❌ Ten gracz jest już w trakcie innego battle.")

    author_data = get_user(ctx.author.id)

    if author_data["money"] < amount:
        return await ctx.send(f"❌ Masz tylko **{format_money(author_data['money'])}**")

    total_pot = amount * 2
    winner_prize = int(total_pot * 0.9)

    embed = discord.Embed(
        title="⚔️ NEON CASINO BATTLE",
        description=(
            f"{ctx.author.mention} wyzywa {member.mention} na pojedynek!\n\n"
            f"**Stawka od osoby:** **{format_money(amount)}**\n"
            f"**Cała pula:** **{format_money(total_pot)}**\n"
            f"**Wygrana:** **{format_money(winner_prize)}**\n\n"
            f"{member.mention}, kliknij `✅`, aby zaakceptować."
        ),
        color=0xF5C542
    )
    embed.set_footer(text="Masz 20 sekund na akceptację • 10% puli dla kasyna")
    set_embed_thumbnail(embed, ctx.author)

    msg = await ctx.send(embed=embed)
    await msg.add_reaction("✅")

    ACTIVE_BATTLES[msg.id] = {
        "channel_id": ctx.channel.id,
        "author_id": ctx.author.id,
        "enemy_id": member.id,
        "amount": amount,
        "author_obj": ctx.author,
        "enemy_obj": member
    }
    ACTIVE_BATTLE_USERS.add(ctx.author.id)
    ACTIVE_BATTLE_USERS.add(member.id)

    def check(reaction, user):
        return (
            reaction.message.id == msg.id and
            str(reaction.emoji) == "✅" and
            user.id == member.id
        )

    try:
        await bot.wait_for("reaction_add", timeout=20.0, check=check)
    except asyncio.TimeoutError:
        cleanup_battle(msg.id)
        cancel_embed = discord.Embed(
            title="❌ BATTLE ANULOWANE",
            description="Wyzwanie nie zostało zaakceptowane na czas.",
            color=0xFF4D6D
        )
        return await msg.edit(embed=cancel_embed)

    battle_data = ACTIVE_BATTLES.get(msg.id)
    if not battle_data:
        return

    author_data = get_user(ctx.author.id)
    enemy_data = get_user(member.id)

    if author_data["money"] < amount:
        cleanup_battle(msg.id)
        return await msg.edit(embed=discord.Embed(
            title="❌ BATTLE ANULOWANE",
            description="Osoba wyzywająca nie ma już wystarczającej ilości pieniędzy.",
            color=0xFF4D6D
        ))

    if enemy_data["money"] < amount:
        cleanup_battle(msg.id)
        return await msg.edit(embed=discord.Embed(
            title="❌ BATTLE ANULOWANE",
            description=f"{member.mention} nie ma już wystarczającej ilości pieniędzy.",
            color=0xFF4D6D
        ))

    author_data["money"] -= amount
    enemy_data["money"] -= amount
    save()

    try:
        await msg.clear_reactions()
    except discord.Forbidden:
        pass
    except discord.HTTPException:
        pass

    casino_cut = total_pot - winner_prize

    battle_frames = [
        f"⚔️ {ctx.author.display_name} VS {member.display_name}",
        f"💥 {ctx.author.display_name} VS {member.display_name}",
        f"⚡ {ctx.author.display_name} VS {member.display_name}",
        f"🔥 {ctx.author.display_name} VS {member.display_name}",
        f"💢 {ctx.author.display_name} VS {member.display_name}"
    ]

    delay = 1.0 / len(battle_frames)

    for i, frame in enumerate(battle_frames):
        spin_embed = discord.Embed(
            title="⚔️ NEON CASINO BATTLE",
            description=(
                f"**{ctx.author.mention}** vs **{member.mention}**\n"
                f"**Stawka od osoby:** **{format_money(amount)}**\n"
                f"**Cała pula:** **{format_money(total_pot)}**\n\n"
                f"`{frame}`"
            ),
            color=0xF5C542 if i % 2 == 0 else 0x11131A
        )
        spin_embed.add_field(name="Status", value="`Starcie trwa...`", inline=False)
        await msg.edit(embed=spin_embed)
        await asyncio.sleep(delay)

    winner = random.choice([ctx.author, member])
    loser = member if winner.id == ctx.author.id else ctx.author

    winner_data = get_user(winner.id)
    winner_data["money"] += winner_prize
    save()

    final_embed = discord.Embed(
        title="🏆 BATTLE ZAKOŃCZONE",
        description=(
            f"**Zwycięzca:** {winner.mention}\n"
            f"**Przegrany:** {loser.mention}\n\n"
            f"**Cała pula:** **{format_money(total_pot)}**\n"
            f"**Dla zwycięzcy:** **{format_money(winner_prize)}**\n"
            f"**Dla kasyna:** **{format_money(casino_cut)}**"
        ),
        color=0x57F287
    )
    final_embed.set_footer(text="Only one leaves with the prize")
    set_embed_thumbnail(final_embed, winner)

    cleanup_battle(msg.id)
    await msg.edit(embed=final_embed)


@battle.error
async def battle_error(ctx, error):
    if isinstance(error, commands.CommandOnCooldown):
        return await ctx.send(f"⏳ Następne wyzwanie za **{error.retry_after:.1f}s**")
    if isinstance(error, commands.MissingRequiredArgument):
        return await ctx.send("❌ Użyj: `!battle @osoba kwota`")
    if isinstance(error, commands.BadArgument):
        return await ctx.send("❌ Użyj poprawnie: `!battle @osoba kwota`")


# =====================
# BLACKJACK
# =====================
@bot.command(aliases=["bj"])
@commands.cooldown(1, 3, commands.BucketType.user)
async def blackjack(ctx, amount: int):
    if amount <= 0:
        return await ctx.send("❌ Kwota musi być większa niż 0")

    data = get_user(ctx.author.id)

    if data["money"] < amount:
        return await ctx.send(f"❌ Masz tylko **{format_money(data['money'])}**")

    neon_gold = 0xF5C542
    neon_red = 0xFF4D6D
    neon_green = 0x57F287
    dark_casino = 0x11131A

    values = {
        "2": 2, "3": 3, "4": 4, "5": 5, "6": 6,
        "7": 7, "8": 8, "9": 9, "10": 10,
        "J": 10, "Q": 10, "K": 10, "A": 11
    }

    def create_deck():
        suits = ["♠", "♥", "♦", "♣"]
        ranks = ["2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A"]
        deck = [f"{rank}{suit}" for suit in suits for rank in ranks]
        random.shuffle(deck)
        return deck

    def hand_value(hand):
        total = 0
        aces = 0

        for card in hand:
            rank = card[:-1]
            total += values[rank]
            if rank == "A":
                aces += 1

        while total > 21 and aces > 0:
            total -= 10
            aces -= 1

        return total

    def format_hand(hand, hide_second=False):
        if hide_second and len(hand) >= 2:
            return f"`{hand[0]}` `🂠`"
        return " ".join(f"`{card}`" for card in hand)

    def result_embed(title, color, player_hand, dealer_hand, desc, balance_text):
        embed = discord.Embed(
            title=title,
            description=(
                f"**Gracz:** {ctx.author.mention}\n"
                f"**Stawka:** **{format_money(amount)}**\n\n"
                f"**Twoje karty:** {format_hand(player_hand)}\n"
                f"**Suma:** **{hand_value(player_hand)}**\n\n"
                f"**Krupier:** {format_hand(dealer_hand)}\n"
                f"**Suma krupiera:** **{hand_value(dealer_hand)}**\n\n"
                f"{desc}\n\n"
                f"**Saldo:** **{balance_text}**"
            ),
            color=color
        )
        set_embed_thumbnail(embed, ctx.author)
        embed.set_footer(text="🃏 Neon Casino • Blackjack")
        return embed

    deck = create_deck()
    player_hand = [deck.pop(), deck.pop()]
    dealer_hand = [deck.pop(), deck.pop()]

    data["money"] -= amount
    save()

    player_blackjack = hand_value(player_hand) == 21
    dealer_blackjack = hand_value(dealer_hand) == 21

    if player_blackjack or dealer_blackjack:
        if player_blackjack and dealer_blackjack:
            data["money"] += amount
            save()
            embed = result_embed(
                "🤝 REMIS",
                neon_gold,
                player_hand,
                dealer_hand,
                f"Obie strony mają blackjacka. Stawka **{format_money(amount)}** wraca do Ciebie.",
                format_money(data["money"])
            )
            return await ctx.send(embed=embed)

        if player_blackjack:
            winnings = int(amount * 2.5)
            data["money"] += winnings
            save()
            embed = result_embed(
                "🃏 BLACKJACK!",
                neon_green,
                player_hand,
                dealer_hand,
                f"🎉 Naturalny blackjack! Wygrywasz **+{format_money(winnings)}**",
                format_money(data["money"])
            )
            return await ctx.send(embed=embed)

        save()
        embed = result_embed(
            "💸 PRZEGRANA",
            neon_red,
            player_hand,
            dealer_hand,
            f"Krupier ma blackjacka. Tracisz **-{format_money(amount)}**",
            format_money(data["money"])
        )
        return await ctx.send(embed=embed)

    start_embed = discord.Embed(
        title="🃏 NEON CASINO",
        description=(
            f"**Gracz:** {ctx.author.mention}\n"
            f"**Stawka:** **{format_money(amount)}**\n\n"
            f"**Twoje karty:** {format_hand(player_hand)}\n"
            f"**Suma:** **{hand_value(player_hand)}**\n\n"
            f"**Krupier:** {format_hand(dealer_hand, hide_second=True)}\n\n"
            f"Zareaguj:\n"
            f"`✋` - dobierz kartę\n"
            f"`🛑` - zostań"
        ),
        color=dark_casino
    )
    set_embed_thumbnail(start_embed, ctx.author)
    start_embed.set_footer(text="Masz 20 sekund na ruch")

    msg = await ctx.send(embed=start_embed)
    await msg.add_reaction("✋")
    await msg.add_reaction("🛑")

    def check(reaction, user):
        return (
            user == ctx.author and
            reaction.message.id == msg.id and
            str(reaction.emoji) in ["✋", "🛑"]
        )

    stood = False

    while hand_value(player_hand) < 21 and not stood:
        try:
            reaction, user = await bot.wait_for("reaction_add", timeout=20.0, check=check)
        except asyncio.TimeoutError:
            stood = True
            break

        emoji = str(reaction.emoji)

        try:
            await msg.remove_reaction(reaction.emoji, user)
        except discord.Forbidden:
            pass
        except discord.HTTPException:
            pass

        if emoji == "✋":
            player_hand.append(deck.pop())

            hit_embed = discord.Embed(
                title="🃏 NEON CASINO",
                description=(
                    f"**Gracz:** {ctx.author.mention}\n"
                    f"**Stawka:** **{format_money(amount)}**\n\n"
                    f"**Twoje karty:** {format_hand(player_hand)}\n"
                    f"**Suma:** **{hand_value(player_hand)}**\n\n"
                    f"**Krupier:** {format_hand(dealer_hand, hide_second=True)}\n\n"
                    f"`✋` - dobierz kartę\n"
                    f"`🛑` - zostań"
                ),
                color=neon_gold
            )
            set_embed_thumbnail(hit_embed, ctx.author)
            hit_embed.set_footer(text="Blackjack w toku")
            await msg.edit(embed=hit_embed)

        elif emoji == "🛑":
            stood = True

    player_total = hand_value(player_hand)

    if player_total > 21:
        bust_embed = result_embed(
            "💸 PRZEGRANA",
            neon_red,
            player_hand,
            dealer_hand,
            f"Przekroczyłeś 21. Kasyno zabiera **-{format_money(amount)}**",
            format_money(data["money"])
        )
        return await msg.edit(embed=bust_embed)

    while hand_value(dealer_hand) < 17:
        dealer_hand.append(deck.pop())
        await asyncio.sleep(0.5)

    dealer_total = hand_value(dealer_hand)

    if dealer_total > 21 or player_total > dealer_total:
        winnings = amount * 2
        data["money"] += winnings
        save()

        win_embed = result_embed(
            "🎉 WYGRANA",
            neon_green,
            player_hand,
            dealer_hand,
            f"Wygrałeś rozdanie! Otrzymujesz **+{format_money(winnings)}**",
            format_money(data["money"])
        )
        await msg.edit(embed=win_embed)

    elif player_total == dealer_total:
        data["money"] += amount
        save()

        draw_embed = result_embed(
            "🤝 REMIS",
            neon_gold,
            player_hand,
            dealer_hand,
            f"Remis. Stawka **{format_money(amount)}** wraca do Ciebie.",
            format_money(data["money"])
        )
        await msg.edit(embed=draw_embed)

    else:
        lose_embed = result_embed(
            "💸 PRZEGRANA",
            neon_red,
            player_hand,
            dealer_hand,
            f"Krupier wygrywa rozdanie. Tracisz **-{format_money(amount)}**",
            format_money(data["money"])
        )
        await msg.edit(embed=lose_embed)


@blackjack.error
async def blackjack_error(ctx, error):
    if isinstance(error, commands.CommandOnCooldown):
        return await ctx.send(f"⏳ Następna gra w blackjacka za **{error.retry_after:.1f}s**")
    if isinstance(error, commands.MissingRequiredArgument):
        return await ctx.send("❌ Użyj: `!blackjack (kwota)`")
    if isinstance(error, commands.BadArgument):
        return await ctx.send("❌ Kwota musi być liczbą, np. `!blackjack 500`")


# =====================
# JACKPOT
# =====================
@bot.command()
@commands.cooldown(1, 5, commands.BucketType.channel)
async def jackpot(ctx, amount: int):
    channel_id = ctx.channel.id

    if channel_id in ACTIVE_JACKPOTS:
        return await ctx.send("❌ Na tym kanale jackpot jest już aktywny. Użyj `!joinpot kwota`, aby dołączyć.")

    if amount <= 0:
        return await ctx.send("❌ Kwota musi być większa niż 0")

    host_data = get_user(ctx.author.id)

    if host_data["money"] < amount:
        return await ctx.send(f"❌ Masz tylko **{format_money(host_data['money'])}**")

    host_data["money"] -= amount
    save()

    ACTIVE_JACKPOTS[channel_id] = {
        "host_id": ctx.author.id,
        "players": {
            str(ctx.author.id): {
                "user": ctx.author,
                "amount": amount
            }
        }
    }

    neon_gold = 0xF5C542
    dark_casino = 0x11131A

    embed = discord.Embed(
        title="🎰 JACKPOT",
        description=(
            f"**Host:** {ctx.author.mention}\n"
            f"**Startowa wpłata:** **{format_money(amount)}**\n"
            f"**Czas na dołączenie:** **20s**\n\n"
            f"Użyj `!joinpot kwota`, aby wejść do gry."
        ),
        color=dark_casino
    )
    embed.add_field(name="Pula", value=f"**{format_money(amount)}**", inline=True)
    embed.add_field(name="Gracze", value="**1**", inline=True)
    embed.set_footer(text="Wygrany zgarnia 90% puli • 10% dla kasyna")
    set_embed_thumbnail(embed, ctx.author)

    msg = await ctx.send(embed=embed)

    for seconds_left in [15, 10, 5]:
        await asyncio.sleep(5)

        jackpot_data = ACTIVE_JACKPOTS.get(channel_id)
        if jackpot_data is None:
            return

        total_pot = sum(player["amount"] for player in jackpot_data["players"].values())
        player_list = "\n".join(
            f"{info['user'].mention} — **{format_money(info['amount'])}**"
            for info in jackpot_data["players"].values()
        )

        update_embed = discord.Embed(
            title="🎰 JACKPOT",
            description=(
                f"**Do końca:** **{seconds_left}s**\n\n"
                f"Użyj `!joinpot kwota`, aby wejść do gry."
            ),
            color=neon_gold if seconds_left <= 10 else dark_casino
        )
        update_embed.add_field(name="Pula", value=f"**{format_money(total_pot)}**", inline=True)
        update_embed.add_field(name="Gracze", value=f"**{len(jackpot_data['players'])}**", inline=True)
        update_embed.add_field(name="Uczestnicy", value=player_list[:1024], inline=False)
        update_embed.set_footer(text="Wygrany zgarnia 90% puli • 10% dla kasyna")

        await msg.edit(embed=update_embed)

    jackpot_data = ACTIVE_JACKPOTS.get(channel_id)
    if jackpot_data is None:
        return

    players = list(jackpot_data["players"].values())
    total_pot = sum(player["amount"] for player in players)

    if len(players) < 2:
        refund_player = players[0]
        refund_data = get_user(refund_player["user"].id)
        refund_data["money"] += refund_player["amount"]
        save()

        cancel_embed = discord.Embed(
            title="❌ JACKPOT ANULOWANY",
            description="Za mało graczy. Stawka została zwrócona.",
            color=0xFF4D6D
        )
        cancel_embed.add_field(name="Zwrócono", value=f"**{format_money(refund_player['amount'])}**", inline=False)

        ACTIVE_JACKPOTS.pop(channel_id, None)
        return await msg.edit(embed=cancel_embed)

    weighted_users = [player["user"] for player in players]
    weighted_amounts = [player["amount"] for player in players]

    winner = random.choices(weighted_users, weights=weighted_amounts, k=1)[0]
    winner_take = int(total_pot * 0.90)
    casino_take = total_pot - winner_take

    winner_data = get_user(winner.id)
    winner_data["money"] += winner_take
    save()

    player_list = "\n".join(
        f"{info['user'].mention} — **{format_money(info['amount'])}**"
        for info in players
    )

    final_embed = discord.Embed(
        title="🏆 JACKPOT ROZSTRZYGNIĘTY",
        description=(
            f"**Zwycięzca:** {winner.mention}\n"
            f"**Cała pula:** **{format_money(total_pot)}**\n"
            f"**Dla zwycięzcy:** **{format_money(winner_take)}**\n"
            f"**Dla kasyna:** **{format_money(casino_take)}**"
        ),
        color=0x57F287
    )
    final_embed.add_field(name="Uczestnicy", value=player_list[:1024], inline=False)
    final_embed.set_footer(text="Jackpot zakończony")
    set_embed_thumbnail(final_embed, winner)

    ACTIVE_JACKPOTS.pop(channel_id, None)
    await msg.edit(embed=final_embed)


@bot.command()
async def joinpot(ctx, amount: int):
    channel_id = ctx.channel.id
    jackpot_data = ACTIVE_JACKPOTS.get(channel_id)

    if jackpot_data is None:
        return await ctx.send("❌ Nie ma teraz aktywnego jackpota na tym kanale. Użyj `!jackpot kwota`.")

    if amount <= 0:
        return await ctx.send("❌ Kwota musi być większa niż 0")

    user_id = str(ctx.author.id)
    data = get_user(ctx.author.id)

    if data["money"] < amount:
        return await ctx.send(f"❌ Masz tylko **{format_money(data['money'])}**")

    data["money"] -= amount
    save()

    if user_id in jackpot_data["players"]:
        jackpot_data["players"][user_id]["amount"] += amount
    else:
        jackpot_data["players"][user_id] = {
            "user": ctx.author,
            "amount": amount
        }

    total_pot = sum(player["amount"] for player in jackpot_data["players"].values())

    embed = discord.Embed(
        title="🎰 DOŁĄCZONO DO JACKPOTA",
        description=(
            f"{ctx.author.mention} dołączył z kwotą **{format_money(amount)}**\n\n"
            f"**Aktualna pula:** **{format_money(total_pot)}**\n"
            f"**Liczba graczy:** **{len(jackpot_data['players'])}**"
        ),
        color=0xF5C542
    )
    set_embed_thumbnail(embed, ctx.author)
    await ctx.send(embed=embed)


@jackpot.error
async def jackpot_error(ctx, error):
    if isinstance(error, commands.CommandOnCooldown):
        return await ctx.send(f"⏳ Następny jackpot na tym kanale za **{error.retry_after:.1f}s**")
    if isinstance(error, commands.MissingRequiredArgument):
        return await ctx.send("❌ Użyj: `!jackpot (kwota)`")
    if isinstance(error, commands.BadArgument):
        return await ctx.send("❌ Kwota musi być liczbą, np. `!jackpot 500`")


@joinpot.error
async def joinpot_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        return await ctx.send("❌ Użyj: `!joinpot (kwota)`")
    if isinstance(error, commands.BadArgument):
        return await ctx.send("❌ Kwota musi być liczbą, np. `!joinpot 500`")


# =====================
# SKLEP
# =====================
@bot.command()
async def sklep(ctx):
    embed = discord.Embed(
        title="🛒 SKLEP",
        description="Dostępne itemy:",
        color=0xFFA500
    )

    for item, price in SHOP_ITEMS.items():
        if item == "burger":
            embed.add_field(name="🍔 Burger", value=f"💰 {format_money(price)}", inline=False)
        elif item in COLOR_ROLES:
            emoji = ROLE_COLOR_EMOJIS.get(item, "⭕")
            embed.add_field(name=f"{emoji} {item.capitalize()}", value=f"💰 {format_money(price)}", inline=False)

    embed.add_field(
        name="JAK KUPIĆ?",
        value="`!kup burger 1`\n`!kup czerwony`",
        inline=False
    )
    embed.set_footer(text="Kupno koloru zmienia poprzedni kolor.")
    await ctx.send(embed=embed)


# =====================
# KUP
# =====================
@bot.command()
async def kup(ctx, item, amount: int = 1):
    item = item.lower()

    if amount <= 0:
        return await ctx.send("❌ Ilość musi być większa niż 0")

    if item not in SHOP_ITEMS:
        return await ctx.send("❌ Tego itemu nie ma w sklepie")

    price = SHOP_ITEMS[item]
    data = get_user(ctx.author.id)

    if item in COLOR_ROLES:
        amount = 1

    total_price = price * amount

    if data["money"] < total_price:
        return await ctx.send(
            f"❌ Masz tylko **{format_money(data['money'])}**, potrzebujesz **{format_money(total_price)}**"
        )

    data["money"] -= total_price

    if item in COLOR_ROLES:
        for role_name in COLOR_ROLES.values():
            old_role = discord.utils.get(ctx.guild.roles, name=role_name)
            if old_role and old_role in ctx.author.roles:
                await ctx.author.remove_roles(old_role)

        new_role = discord.utils.get(ctx.guild.roles, name=COLOR_ROLES[item])
        if new_role:
            await ctx.author.add_roles(new_role)

        data["color"] = item
        save()

        emoji = ROLE_COLOR_EMOJIS.get(item, "⭕")
        embed = discord.Embed(
            title="🎨 KOLOR ZMIENIONY!",
            description=f"Kupiłeś kolor {emoji} **{item.capitalize()}**",
            color=0x51CF66
        )
        set_embed_thumbnail(embed, ctx.author)
        return await ctx.send(embed=embed)

    if item not in data["inv"]:
        data["inv"][item] = 0
    data["inv"][item] += amount
    save()

    embed = discord.Embed(
        title="🛍️ ZAKUP!",
        description=f"Kupiłeś **{item} x{amount}**",
        color=0x51CF66
    )
    embed.add_field(name="Razem w ekwipunku", value=f"x{data['inv'][item]}")
    set_embed_thumbnail(embed, ctx.author)
    await ctx.send(embed=embed)


# =====================
# EQ
# =====================
@bot.command()
async def eq(ctx):
    data = get_user(ctx.author.id)

    embed = discord.Embed(
        title="🎒 EKWIPUNEK",
        description=ctx.author.name,
        color=0x00BCD4
    )

    if not data["inv"]:
        embed.add_field(name="📦 ITEMY", value="Brak itemów", inline=False)
    else:
        items_text = ""
        for item, amount in data["inv"].items():
            emoji = "🍔" if item == "burger" else "📦"
            items_text += f"{emoji} **{item.capitalize()}** x{amount}\n"
        embed.add_field(name="📦 ITEMY", value=items_text, inline=False)

    embed.add_field(name="💰 KASA", value=f"**{format_money(data['money'])}**", inline=False)

    if data["color"]:
        emoji = ROLE_COLOR_EMOJIS.get(data["color"], "⭕")
        embed.set_footer(text=f"Kolor: {emoji} {data['color'].capitalize()}")

    set_embed_thumbnail(embed, ctx.author)
    await ctx.send(embed=embed)


# =====================
# GLOBAL ERROR
# =====================
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return
    if isinstance(error, commands.MissingRequiredArgument):
        return await ctx.send("❌ Brakuje argumentów do tej komendy.")
    if isinstance(error, commands.BadArgument):
        return await ctx.send("❌ Podano zły argument do komendy.")
    if isinstance(error, commands.CheckFailure):
        return await ctx.send("❌ Nie masz uprawnień do tej komendy.")
    raise error


# =====================
# START
# =====================
bot.run(os.getenv("TOKEN"))
