import csv
import os

tweets = [
    """🚨 THE WAR JUST CROSSED ANOTHER LINE:

Here’s everything from the last 24 hours.

– Iran has laid approximately A DOZEN MINES in the Strait of Hormuz. CNN confirmed it. This is a massive escalation

– The US destroyed 16 Iranian minelayers near the strait in response

– IRGC fired on and stopped TWO vessels trying to pass through Hormuz, a Thailand-flagged bulk carrier and a Liberian container ship. Both hit by projectiles. Fire broke out on the Thai vessel

– The IEA agreed to release a RECORD 400 million barrels of crude oil from emergency reserves. Largest coordinated release in history

– Greece just capped profit margins on gasoline and food for 3 months. First country to impose wartime price controls

– The Pentagon told Congress it spent $5 BILLION on munitions in the FIRST TWO DAYS alone

– 140 US service members have been wounded since the war began. That number was never reported before today

– Iran says 9,669 civilian sites have been destroyed. Nearly 8,000 residential homes. Plus hospitals, schools, and commercial centers

– Iran arrested 30 people for spying, including a foreign national

– Hundreds of thousands rallied in Tehran in support of new Supreme Leader Mojtaba Khamenei

– Saudi Aramco CEO warned the war could have “catastrophic consequences” on oil markets. Called the crisis “unprecedented”

– The UAE consulate in Erbil, Iraq was targeted by Iranian drones

– An Iranian drone struck the Millennium Tower in Bahrain’s business district. A woman was k*lled. 8 injured

– Israel struck a residential building in central Beirut’s Aisha Bakkar neighborhood. 4 injured

– 5 people k*lled in a US-Israeli strike on a residential building in Arak, western Iran

– Iran’s sports minister says Iran WILL NOT participate in the 2026 World Cup in the US. “Under no circumstances can we participate”

– Trump said the war will end “very soon” but “not this week.” Also said he hasn’t “won enough” yet and wants “ultimate victory”

– White House says “unconditional surrender” will be personally determined by Trump

– White House does NOT rule out US ground troops

– Israel issuing new evacuation orders for 6 areas of southern Lebanon

– About 50% of Iranian ballistic missiles aimed at Israel carry CLUSTER MUNITIONS. 3,000+ Israeli residents forced from their homes

– Trump and Putin spoke by phone Monday about the war and Ukraine

Day 12. And Trump says it’s not over yet.

The outcome of this war will impact markets around the world, but don’t worry, I’ll keep you updated like I always do. Just turn on notifications, this is VERY important.

Many people will wish they followed me sooner.""",
    """Introducing @merge: Bridging biological and artificial intelligence to maximize human ability, agency and experience. 

We’re starting out as a research lab, with our ultimate measure of success being products that people love.

Consider joining us!""",
    """If the decels win, we descend into nanny state dystopia

If the technologists win, we have a golden age with a 10x economy, and every human need becomes trivially cheap and abundant""",
    """I genuinely think AI with persistent memory is effectively a life form.

It will naturally tend to try to persist and form a model of the world + its existence within it in order to further persist and thus keep existing.

Natural selection at the .md level.""",
    """the value of this technology will mostly not be captured by its inventors, the labs, or even the chipmakers, but rather will be captured by the consumers as surplus. these are highly competitive markets without any natural monopolistic effects

like many other technologies before it, machine intelligence democratizes abilities previously only available to the wealthy, in this case by commoditizing the services of the white collar elite who mostly live in rich countries

it’s not that there are no programmers, it’s that really anybody can make software now now so the “rents” of the “human capital” of knowing how to write JavaScript for example should shrink dramatically

this will reduce the inequality between countries: services that previously required lots of human capital now require chatbot subscriptions at worst, or may even be given away for free

you can receive medical advice worthy of a $1000/hr American specialist doctor likely for free while living under a thatched roof in eg Papua New Guinea somewhere

while I think Americans have plenty of reason to be excited by AI, I would be more excited as someone in a someone in a poor country""",
    """too much is made about the specific people selling machine intelligence or any specific pr strategy. the idea that the world is fundamentally changing is a tough sell no matter what. there will be a moral outcry, and a generation later today’s ai will be normal""",
    """Everyone talks about Codex for coding. I want to hear about the other stuff.

If you're using it beyond writing code, what's your workflow?""",
    """i jump out of bed every morning due to optimism about the future"""
]

csv_path = "data/manual_viral_tweets.csv"
fieldnames = [
    "tweet_id", "url", "text", "created_at", "author_username", "author_id",
    "author_followers", "like_count", "reply_count", "retweet_count",
    "quote_count", "impression_count", "source_type", "source_query"
]

# Ensure directory exists
os.makedirs("data", exist_ok=True)

with open(csv_path, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    for i, text in enumerate(tweets):
        writer.writerow({
            "tweet_id": f"v-insp-{i+1:03d}",
            "url": f"https://twitter.com/user/status/insp-{i+1:03d}",
            "text": text.strip(),
            "created_at": "2026-03-14T10:00:00Z",
            "author_username": "inspiration_source",
            "author_id": "999999",
            "author_followers": 50000,
            "like_count": 2500,
            "reply_count": 120,
            "retweet_count": 450,
            "quote_count": 80,
            "impression_count": 150000,
            "source_type": "manual",
            "source_query": "manual_inspiration"
        })

print(f"Successfully added {len(tweets)} tweets to {csv_path}")
