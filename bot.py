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
bot.remove_command('help')  # Usuń wbudowaną komendę help

# =====================
# PLIKI
# =====================
DATA_FILE = "users.json"
COOLDOWN_FILE = "cooldowns.json"
DAILY_FILE = "daily.json"

# =====================
# SKLEP
# =====================
shop_items = {
    "burger": 100,
    "czerwony": 500,
    "niebieski": 500,
    "zielony": 500,
    "zolty": 500,
    "fioletowy": 500,
    "rozowy": 500
}

color_roles = {
    "czerwony": "CZERWONY",
    "niebieski": "NIEBIESKI",
    "zielony": "ZIELONY",
    "zolty": "ZOLTY",
    "fioletowy": "FIOLETOWY",
    "rozowy": "ROZOWY"
}

color_emojis = {
    "czarny": "⚫",
    "czerwony": "🔴",
    "zielony": "🟢"
}

# =====================
# PROFESJE
# =====================
professions = {
    "SĘDZIA": 500,
    "PSYCHOLOG": 400,
    "ADWOKAT": 250
}

# =====================
# SLOTY
# =====================
slot_emojis = ["🍎", "🍊", "🍋", "🍌", "🍉", "🍇", "🍓", "⭐", "💎", "💰"]

# =====================
# LOAD
# =====================
def load(path, default):
    if os.path.exists(path):
        with open(path, "r") as f:
            return json.load(f)
    return default

users = load(DATA_FILE, {})
cooldowns = load(COOLDOWN_FILE, {})
daily_data = load(DAILY_FILE, {})

# =====================
# SAVE
# =====================
def save():
    with open(DATA_FILE, "w") as f:
        json.dump(users, f)

def save_cd():
    with open(COOLDOWN_FILE, "w") as f:
        json.dump(cooldowns, f)

def save_daily():
    with open(DAILY_FILE, "w") as f:
        json.dump(daily_data, f)

# =====================
# USER
# =====================
def get_user(user_id):
    user_id = str(user_id)

    if user_id not in users:
        users[user_id] = {"money": 0, "inv": {}, "color": None}
    
    # Upewniaj się, że inv jest słownikiem
    if not isinstance(users[user_id]["inv"], dict):
        users[user_id]["inv"] = {}
    
    # Dodaj "color" jeśli nie istnieje (dla starych danych)
    if "color" not in users[user_id]:
        users[user_id]["color"] = None

    return users[user_id]

# =====================
# READY
# =====================
@bot.event
async def on_ready():
    print(f"✅ Bot działa jako {bot.user}")

# =====================
# KOMENDY
# =====================
@bot.command()
async def komendy(ctx):
    embed = discord.Embed(
        title="📖 KOMENDY BOTA",
        description="Wszystkie dostępne komendy:",
        color=0x5865F2
    )
    
    embed.add_field(name="💰 EKONOMIA", value="`!balance` - Twoja kasa\n`!work` - Pracuj (zarabiaj więcej z rolą!)\n`!daily` - Daily (1000-2000$ co 24h)\n`!pay @osoba kwota` - Wyślij pieniądze", inline=False)
    embed.add_field(name="🛒 SKLEP", value="`!sklep` - Pokaż sklep\n`!kup item ilość` - Kup przedmiot\n`!eq` - Twój ekwipunek", inline=False)
    embed.add_field(name="🎰 HAZARD", value="`!bet kolor kwota` - Postaw na kolor\n`!slot kwota` - Automaty (25% szans na x2.5)\nKolory: czarny, czerwony, zielony", inline=False)
    embed.add_field(name="👑 ADMIN", value="`!addmoney @osoba kwota` - Dodaj pieniądze (tylko owner)", inline=False)
    embed.add_field(name="⚖️ SĄD", value="`!pozew @osoba powód kwota` - Pozwij kogoś\n`!sprawy` - Oczekujące sprawy\n`!wyrok @osoba accept/reject` - Wydaj wyrok (SĘDZIA)\n`!zmienwyrok @osoba raise/lower/przerwa wartość` - Zmień wyrok (SĘDZIA)\n`!historia @osoba` - Historia spraw", inline=False)
    embed.set_thumbnail(url=ctx.bot.user.avatar.url)
    
    await ctx.send(embed=embed)

# =====================
# BALANCE
# =====================
@bot.command()
async def balance(ctx):
    data = get_user(ctx.author.id)
    embed = discord.Embed(
        title="💰 TWOJA KASA",
        description=f"{ctx.author.name}",
        color=0xFFD700
    )
    embed.add_field(name="Pieniądze", value=f"**{data['money']}$**", inline=False)
    embed.set_thumbnail(url=ctx.author.avatar.url)
    await ctx.send(embed=embed)

# =====================
# WORK
# =====================
@bot.command()
async def work(ctx):
    user_id = str(ctx.author.id)
    now = time.time()
    
    # Właściciel nie ma cooldownu
    is_owner = await bot.is_owner(ctx.author)

    if not is_owner and user_id in cooldowns:
        if now - float(cooldowns[user_id]) < 3600:
            left = int(3600 - (now - float(cooldowns[user_id])))
            embed = discord.Embed(
                title="⏳ CZEKAJ!",
                description=f"Wróć za {left//60}m {left%60}s",
                color=0xFF6B6B
            )
            return await ctx.send(embed=embed)

    if not is_owner:
        cooldowns[user_id] = now
        save_cd()

    # Sprawdź profesję
    earnings = 200
    profession = "Pracownik"
    
    for prof_name, prof_earnings in professions.items():
        role = discord.utils.get(ctx.guild.roles, name=prof_name)
        if role and role in ctx.author.roles:
            earnings = prof_earnings
            profession = prof_name
            break
    
    # Ikony profesji
    prof_emojis = {
        "SĘDZIA": "⚖️",
        "PSYCHOLOG": "🧠",
        "ADWOKAT": "📋",
        "Pracownik": "💼"
    }
    emoji = prof_emojis.get(profession, "💼")
    
    data = get_user(user_id)
    data["money"] += earnings
    save()

    embed = discord.Embed(
        title="💪 PRACOWANIE!",
        description=f"{emoji} {profession}\n+{earnings}$",
        color=0x51CF66
    )
    embed.set_thumbnail(url=ctx.author.avatar.url)
    await ctx.send(embed=embed)

# =====================
# DAILY
# =====================
@bot.command()
async def daily(ctx):
    user_id = str(ctx.author.id)
    now = time.time()

    if user_id in daily_data:
        if now - float(daily_data[user_id]) < 86400:
            left = int(86400 - (now - float(daily_data[user_id])))
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
        description=f"Otrzymałeś **{reward}$**",
        color=0xFFD700
    )
    embed.set_thumbnail(url=ctx.author.avatar.url)
    await ctx.send(embed=embed)

# =====================
# PAY
# =====================
@bot.command()
async def pay(ctx, member: discord.Member, amount: int):
    if amount <= 0:
        embed = discord.Embed(title="❌ BŁĄD", description="Kwota musi być większa niż 0", color=0xFF6B6B)
        return await ctx.send(embed=embed)

    sender_id = str(ctx.author.id)
    receiver_id = str(member.id)

    sender_data = get_user(sender_id)

    if sender_data["money"] < amount:
        embed = discord.Embed(title="❌ BŁĄD", description=f"Masz tylko {sender_data['money']}$", color=0xFF6B6B)
        return await ctx.send(embed=embed)

    sender_data["money"] -= amount
    receiver_data = get_user(receiver_id)
    receiver_data["money"] += amount

    save()

    embed = discord.Embed(
        title="💸 TRANSFER",
        description=f"{ctx.author.name} → {member.name}\n**{amount}$**",
        color=0x51CF66
    )
    await ctx.send(embed=embed)

# =====================
# ADDMONEY (ADMIN)
# =====================
@bot.command()
@commands.is_owner()
async def addmoney(ctx, member: discord.Member, amount: int):
    if amount <= 0:
        embed = discord.Embed(title="❌ BŁĄD", description="Kwota musi być większa niż 0", color=0xFF6B6B)
        return await ctx.send(embed=embed)

    data = get_user(member.id)
    data["money"] += amount
    save()

    embed = discord.Embed(
        title="👑 ADMIN",
        description=f"Dodano {amount}$ dla {member.name}",
        color=0x9C27B0
    )
    embed.add_field(name="Nowa kasa", value=f"**{data['money']}$**")
    await ctx.send(embed=embed)

# =====================
# SETMONEY (ADMIN)
# =====================
@bot.command()
@commands.is_owner()
async def setmoney(ctx, member: discord.Member, amount: int):
    if amount < 0:
        embed = discord.Embed(
            title="❌ BŁĄD",
            description="Kwota nie może być ujemna",
            color=0xFF6B6B
        )
        return await ctx.send(embed=embed)

    data = get_user(member.id)
    data["money"] = amount
    save()

    embed = discord.Embed(
        title="💰 USTAWIONO KASĘ",
        description=f"{member.name} ma teraz **{amount}$**",
        color=0x00C853
    )
    embed.set_thumbnail(url=member.avatar.url)
    await ctx.send(embed=embed)

# =====================
# BET (HAZARD)
# =====================
@bot.command()
async def bet(ctx, color, amount: int):
    color = color.lower()
    user_id = str(ctx.author.id)
    now = time.time()
    
    # Walidacja
    if color not in ["czarny", "czerwony", "zielony"]:
        embed = discord.Embed(title="❌ BŁĄD", description="Kolory: **czarny, czerwony, zielony**", color=0xFF6B6B)
        return await ctx.send(embed=embed)
    
    if amount <= 0:
        embed = discord.Embed(title="❌ BŁĄD", description="Kwota musi być większa niż 0", color=0xFF6B6B)
        return await ctx.send(embed=embed)
    
    data = get_user(ctx.author.id)
    
    if data["money"] < amount:
        embed = discord.Embed(title="❌ BRAK KASY", description=f"Masz tylko **{data['money']}$**", color=0xFF6B6B)
        return await ctx.send(embed=embed)
    
    # Wcięcie pieniędzy
    data["money"] -= amount
    save()
    
    # Animacja losowania
    embed = discord.Embed(
        title="🎰 HAZARD",
        description=f"Wybór: {color_emojis[color]}\nStawka: **{amount}$**",
        color=0xFF6B6B
    )
    embed.add_field(name="Losowanie...", value="⏳", inline=False)
    
    msg = await ctx.send(embed=embed)
    
    # Animacja ruletki
    roulette_frames = [
        "🎰 ⚫ 🔴 🟢",
        "🎰 🔴 🟢 ⚫",
        "🎰 🟢 ⚫ 🔴",
        "🎰 ⚫ 🔴 🟢",
        "🎰 🔴 🟢 ⚫",
        "🎰 🟢 ⚫ 🔴",
    ]
    
    for i in range(6):
        frame = roulette_frames[i % len(roulette_frames)]
        embed.set_field_at(0, name=f"Obrót ruletki... ({i+1}/6)", value=frame, inline=False)
        await msg.edit(embed=embed)
        await asyncio.sleep(0.25)
    
    # Losowanie wyniku - szanse zależą od wybranego koloru
    roll = random.randint(1, 100)
    
    if color == "zielony":
        # Zielony 1%
        if roll == 1:
            result_color = "zielony"
            multiplier = 10
        elif roll <= 50:
            result_color = "czarny"
            multiplier = 2
        else:
            result_color = "czerwony"
            multiplier = 2
    else:
        # Czarny/Czerwony 20%, ale zielony zawsze 1%
        if roll == 1:
            result_color = "zielony"
            multiplier = 10
        elif roll <= 20:
            result_color = color
            multiplier = 2
        else:
            # Pozostały kolor (czarny lub czerwony - nie zielony!)
            other_color = "czarny" if color == "czerwony" else "czerwony"
            result_color = other_color
            multiplier = 2
    
    # Obliczenie wyniku
    if result_color == color:
        winnings = amount * multiplier
        data["money"] += winnings
        save()
        
        result_emoji = "✅"
        result_text = f"WYGRANA! 🎉\nWylosowany kolor: {color_emojis[result_color]}\nWygrana: **+{winnings}$** (x{multiplier})\nAktualna kasa: **{data['money']}$**"
        embed_color = 0x51CF66
    else:
        result_emoji = "❌"
        result_text = f"PRZEGRANA!\nWylosowany kolor: {color_emojis[result_color]}\nStrata: **{amount}$**\nAktualna kasa: **{data['money']}$**"
        embed_color = 0xFF8C8C
    
    # Wyświetl wynik
    embed = discord.Embed(
        title="🎰 HAZARD",
        description=result_text,
        color=embed_color
    )
    embed.set_thumbnail(url=ctx.author.avatar.url)
    
    await msg.edit(embed=embed)

# =====================
# BATTLE (WALKA)
# =====================
@bot.command()
async def battle(ctx, member: discord.Member, amount: int):
    if member == ctx.author:
        return await ctx.send("❌ Nie możesz walczyć ze sobą")

    if amount <= 0:
        return await ctx.send("❌ Kwota musi być większa niż 0")

    user1 = get_user(ctx.author.id)
    user2 = get_user(member.id)

    if user1["money"] < amount:
        return await ctx.send("❌ Nie masz tyle pieniędzy")

    if user2["money"] < amount:
        return await ctx.send("❌ Ta osoba nie ma tyle pieniędzy")

    embed = discord.Embed(
        title="⚔️ WYZWANIE DO WALKI",
        description=f"{ctx.author.mention} wyzywa {member.mention} na walkę o **{amount}$**\n\nKliknij ✅ aby zaakceptować",
        color=0xFFA500
    )

    msg = await ctx.send(embed=embed)
    await msg.add_reaction("✅")

    def check(reaction, user):
        return user == member and str(reaction.emoji) == "✅" and reaction.message.id == msg.id

    try:
        await bot.wait_for("reaction_add", timeout=30.0, check=check)
    except asyncio.TimeoutError:
        return await ctx.send("⏳ Czas minął, brak odpowiedzi")

    # Sprawdź jeszcze raz kasę (bo mogła się zmienić)
    if user1["money"] < amount or user2["money"] < amount:
        return await ctx.send("❌ Ktoś nie ma już pieniędzy")

    # Zabierz kasę
    user1["money"] -= amount
    user2["money"] -= amount
    save()

    # Animacja walki
    fight_msg = await ctx.send("⚔️ Walka trwa...")

    await asyncio.sleep(2)

    winner = random.choice([ctx.author, member])
    loser = member if winner == ctx.author else ctx.author

    winnings = int(amount * 2 * 0.75)

    winner_data = get_user(winner.id)
    winner_data["money"] += winnings
    save()

    embed = discord.Embed(
        title="🏆 WYNIK WALKI",
        description=f"👑 Wygrywa: {winner.mention}\n💰 Wygrana: **{winnings}$**\n❌ Przegrany: {loser.mention}",
        color=0x51CF66
    )

    await fight_msg.edit(content=None, embed=embed)

# =====================
# SLOT
# =====================
@bot.command()
async def slot(ctx, amount: int):
    user_id = str(ctx.author.id)
    now = time.time()
    
    # Walidacja
    if amount <= 0:
        embed = discord.Embed(title="❌ BŁĄD", description="Kwota musi być większa niż 0", color=0xFF6B6B)
        return await ctx.send(embed=embed)
    
    data = get_user(ctx.author.id)
    
    if data["money"] < amount:
        embed = discord.Embed(title="❌ BRAK KASY", description=f"Masz tylko **{data['money']}$**", color=0xFF6B6B)
        return await ctx.send(embed=embed)
    
    # Wcięcie pieniędzy
    data["money"] -= amount
    save()
    
    # Początkowy embed
    embed = discord.Embed(
        title="🎰 AUTOMATY",
        description=f"Stawka: **{amount}$**",
        color=0xFF6B6B
    )
    embed.add_field(name="Zakręcanie...", value="⏳ ⏳ ⏳", inline=False)
    
    msg = await ctx.send(embed=embed)
    
    # Animacja spin (zoptymalizowana)
    for i in range(5):
        r1 = random.choice(slot_emojis)
        r2 = random.choice(slot_emojis)
        r3 = random.choice(slot_emojis)
        
        embed.set_field_at(0, name=f"Spin... ({i+1}/5)", value=f"{r1} {r2} {r3}", inline=False)
        await msg.edit(embed=embed)
        await asyncio.sleep(0.12)
    
    # Finalne rezultaty
    roll = random.randint(1, 100)
    
    if roll <= 25:  # 25% szansa na wygraną
        reel1 = random.choice(slot_emojis)
        reel2 = reel1
        reel3 = reel1
        winnings = int(amount * 2.5)
        data["money"] += winnings
        save()
        
        result_text = f"🎉 JACKPOT! 🎉\n\n{reel1} {reel2} {reel3}\n\nWygrana: **+{winnings}$** (x2.5)\nAktualna kasa: **{data['money']}$**"
        embed_color = 0x51CF66
    else:
        reel1 = random.choice(slot_emojis)
        reel2 = random.choice(slot_emojis)
        reel3 = random.choice(slot_emojis)
        
        result_text = f"Nie tym razem...\n\n{reel1} {reel2} {reel3}\n\nStrata: **{amount}$**\nAktualna kasa: **{data['money']}$**"
        embed_color = 0xFF8C8C
    
    # Wynik
    embed = discord.Embed(
        title="🎰 AUTOMATY",
        description=result_text,
        color=embed_color
    )
    embed.set_thumbnail(url=ctx.author.avatar.url)
    
    await msg.edit(embed=embed)

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

    # ITEMY
    for item, price in shop_items.items():
        if item == "burger":
            embed.add_field(
                name="🍔 Burger",
                value=f"💰 {price}$",
                inline=False
            )
        elif item in color_roles:
            # Kolory
            emojis = {
                "czerwony": "❤️",
                "niebieski": "💙",
                "zielony": "💚",
                "zolty": "💛",
                "fioletowy": "💜",
                "rozowy": "🩷"
            }
            emoji = emojis.get(item, "⭕")
            embed.add_field(
                name=f"{emoji} {item.capitalize()}",
                value=f"💰 {price}$",
                inline=False
            )

    embed.add_field(
        name="  JAK KUPIĆ?",
        value="Wpisz: `!kup burger 1`\nLub: `!kup czerwony`",
        inline=False
    )
    embed.set_footer(text="Kolory zastępują stary kolor!")

    await ctx.send(embed=embed)

# =====================
# KUP
# =====================
@bot.command()
async def kup(ctx, item, amount: int = 1):
    item = item.lower()
    
    if amount <= 0:
        return await ctx.send("❌ Ilość musi być większa niż 0")
    
    if item not in shop_items:
        return await ctx.send("❌ Tego itemu nie ma w sklepie")

    price = shop_items[item]
    data = get_user(ctx.author.id)
    
    # Dla kolorów ilość zawsze = 1
    if item in color_roles:
        amount = 1
    
    total_price = price * amount

    if data["money"] < total_price:
        return await ctx.send(f"❌ Masz tylko {data['money']}$, potrzebujesz {total_price}$")

    data["money"] -= total_price
    
    # KOLORY - zmiana roli
    if item in color_roles:
        # Usuń WSZYSTKIE role kolorów
        for color_name, role_name in color_roles.items():
            old_role = discord.utils.get(ctx.guild.roles, name=role_name)
            if old_role and old_role in ctx.author.roles:
                await ctx.author.remove_roles(old_role)
        
        # Dodaj nową rolę
        new_role = discord.utils.get(ctx.guild.roles, name=color_roles[item])
        if new_role:
            await ctx.author.add_roles(new_role)
        
        data["color"] = item
        emojis_map = {"czerwony": "❤️", "niebieski": "💙", "zielony": "💚", "zolty": "💛", "fioletowy": "💜", "rozowy": "🩷"}
        emoji = emojis_map.get(item, "⭕")
        
        embed = discord.Embed(
            title="🎨 KOLOR ZMIENIONY!",
            description=f"Kupiłeś kolor {emoji} {item.capitalize()}",
            color=0x51CF66
        )
        embed.set_thumbnail(url=ctx.author.avatar.url)
        await ctx.send(embed=embed)
    
    # NORMALNE ITEMY - dodaj do ekwipunku
    else:
        if item not in data["inv"]:
            data["inv"][item] = 0
        data["inv"][item] += amount
        
        embed = discord.Embed(
            title="🛍️ ZAKUP!",
            description=f"Kupiłeś {item} x{amount}",
            color=0x51CF66
        )
        embed.add_field(name="Razem w ekwipunku", value=f"x{data['inv'][item]}")
        embed.set_thumbnail(url=ctx.author.avatar.url)
        await ctx.send(embed=embed)

    save()

# =====================
# EQ
# =====================
@bot.command()
async def eq(ctx):
    data = get_user(ctx.author.id)

    embed = discord.Embed(
        title=f"🎒 EKWIPUNEK",
        description=f"{ctx.author.name}",
        color=0x00BCD4
    )

    if not data["inv"]:
        embed.add_field(name="📦 ITEMY", value="Brak itemów", inline=False)
    else:
        items_text = ""
        for item, amount in data["inv"].items():
            items_text += f"🍔 **{item.capitalize()}** x{amount}\n"
        embed.add_field(name="📦 ITEMY", value=items_text, inline=True)

    embed.add_field(name="💰 KASA", value=f"**{data['money']}$**", inline=True)
    embed.set_thumbnail(url=ctx.author.avatar.url)
    
    if data["color"]:
        emojis_map = {"czerwony": "❤️", "niebieski": "💙", "zielony": "💚", "zolty": "💛", "fioletowy": "💜", "rozowy": "🩷"}
        emoji = emojis_map.get(data["color"], "⭕")
        embed.set_footer(text=f"Kolor: {emoji} {data['color'].capitalize()}")

    await ctx.send(embed=embed)

# =====================
# START
# =====================
bot.run(os.getenv("TOKEN"))
