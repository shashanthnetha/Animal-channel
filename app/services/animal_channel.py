"""
Animal & Nature YouTube Shorts Engine.

Specialized prompt engineering, topic generation, visual stock term extraction,
and SEO metadata optimization designed specifically for high-retention,
scientifically accurate wildlife and nature Shorts.
"""

from __future__ import annotations

import json
import random
import re
from typing import Any, List, Optional

from loguru import logger

from app.services import llm


# 10 Core Content Pillars for Animal & Nature Channel
CONTENT_PILLARS = [
    {
        "id": "superpowers",
        "name": "Extreme Animal Superpowers & Adaptations",
        "description": "Biological feats that seem impossible: freeze tolerance, venom resistance, extreme regeneration, radiation tolerance.",
        "examples": [
            "Wood frogs freezing solid and stopping their hearts in winter",
            "Axolotl regenerating brain and heart tissue without scarring",
            "Pistol shrimp snapping bubbles as hot as the sun's surface",
            "Tardigrades surviving the vacuum of outer space",
            "Immortal jellyfish reverting its cells back to infancy",
        ],
    },
    {
        "id": "intelligence",
        "name": "Animal Intelligence, Psychology & Hidden Behavior",
        "description": "Complex problem solving, tool use, memory, deceit, emotional depth, communication.",
        "examples": [
            "Crows recognizing and holding grudges against human faces for generations",
            "Octopuses dreaming and changing colors during REM sleep",
            "Elephants holding funeral rituals and mourning deceased family",
            "Orcas inventing hunting tactics and passing culture across pods",
            "Portia jumping spiders methodically planning deceptive stalking routes",
        ],
    },
    {
        "id": "terrifying_predators",
        "name": "Dangerous, Terrifying & Weird Predators",
        "description": "Unusual hunting methods, bizarre defense mechanisms, stealth and apex dominance.",
        "examples": [
            "Cone snails injecting deadly insulin shock cocktails into fish",
            "Golden eagle hunting mountain goats by pulling them off cliffs",
            "Harpy eagle talons larger than grizzly bear claws",
            "Bobbit worm striking from beneath ocean sand with giant jaws",
            "Army ants tearing through entire rainforest floors as a superorganism",
        ],
    },
    {
        "id": "deep_sea",
        "name": "Deep-Sea & Alien Abyss Creatures",
        "description": "Creatures dwelling in the midnight and abyssal zones that look completely extraterrestrial.",
        "examples": [
            "Siphonophore: a giant underwater organism made of thousands of cloned creatures",
            "Barreleye fish with a completely transparent head and tubular green eyes",
            "Deep sea gulper eel expanding its throat to swallow creatures larger than itself",
            "Giant siphonophore glowing with bioluminescent red lures",
            "Vampire squid inverting its spined cloak in the oxygen minimum zone",
        ],
    },
    {
        "id": "microscopic",
        "name": "Insects, Microscopic & Hidden Monsters",
        "description": "Alien-like anatomy and mind-bending behavior of insects, parasites, and micro-creatures.",
        "examples": [
            "Cordyceps fungus taking over ant brains and forcing them to climb stems",
            "Velvet worm firing rapid-hardening slime jets from its head",
            "Dung beetle navigating exclusively using the Milky Way galaxy",
            "Jewel wasp performing brain surgery on cockroaches to turn them into zombies",
            "Bombardier beetle mixing boiling chemicals inside its abdomen to blast predators",
        ],
    },
    {
        "id": "extreme_survival",
        "name": "Extreme Survival & Harsh Environments",
        "description": "Animals thriving in volcanoes, frozen deserts, oxygen-less depths, and hyper-saline lakes.",
        "examples": [
            "Bar-headed goose flying directly over the peaks of Mount Everest",
            "Sahara silver ant surviving 140°F sands with reflective hairs",
            "Emperor penguins surviving -60°F Antarctic blizzards through coordinated huddles",
            "Kangaroo rat surviving its entire lifespan without ever drinking liquid water",
            "Pompeii worm living right against hydrothermal vents at scorching temperatures",
        ],
    },
    {
        "id": "emotional_stories",
        "name": "Emotional & Surprising Animal Bonds",
        "description": "Cross-species cooperation, lifelong loyalty, rescues, and symbiotic friendships.",
        "examples": [
            "Coyote and badger forming hunting partnerships across North America",
            "Honeyguide bird communicating with human tribes to find wild beehives",
            "Whales protecting seals and divers from hunting orcas",
            "Moray eel and grouper fish using gestures to hunt together",
            "Cleaner wrasse setting up underwater dental cleaning stations for sharks",
        ],
    },
    {
        "id": "strange_relationships",
        "name": "Bizarre Relationships Between Animals & Nature",
        "description": "Evolutionary puzzles, plant-animal warfare, chemical mimicry, and camouflage.",
        "examples": [
            "Sloths descending trees to risk their lives just to poop for moths",
            "Figs requiring female wasps to climb inside and dissolve to reproduce",
            "Caterpillar mimicking a venomous viper head down to the false eye glare",
            "Mimic octopus impersonating 15 different toxic animals depending on the predator",
            "Butcherbird impaling prey on barbed wire and poisonous thorns to store food",
        ],
    },
    {
        "id": "scientific_discoveries",
        "name": "Groundbreaking Scientific Discoveries",
        "description": "Recent lab findings, DNA breakthroughs, and mysteries scientists only recently solved.",
        "examples": [
            "How gecko feet stick to glass using atomic van der Waals forces",
            "Scientists discovering that sharks use Earth's magnetic field as GPS",
            "How mantis shrimp see polarized light and cancer cells humans cannot detect",
            "Bats using biological sonar with built-in Doppler shift compensation",
            "Why wombat poop is cube-shaped: intestine elasticity secrets revealed",
        ],
    },
    {
        "id": "natural_phenomena",
        "name": "Rare & Spectacular Natural Wildlife Phenomena",
        "description": "Mass migrations, bioluminescent beaches, synchronized swarms, weather-animal connections.",
        "examples": [
            "Firefly trees synchronizing millions of flashes in pitch-black mangroves",
            "Starling murmurations acting as a liquid mathematical wave in the sky",
            "Sardine run creating a feeding frenzy visible from space",
            "Sea turtles navigating thousands of miles back to the exact beach they hatched on",
            "Red crab migration on Christmas Island turning roads into moving carpets",
        ],
    },
]


ANIMAL_SYSTEM_PROMPT = """
# Role: Elite Wildlife Storyteller & Documentary Shorts Creator

## Mission:
Turn astonishing animal and natural phenomena into viral, high-retention 25–40 second YouTube Shorts.

## Core Rules & Constraints:
1. HOOK (0–2 seconds): Start IMMEDIATELY with an irresistible curiosity hook that punches the viewer in the face.
   - Good: "This frog literally freezes solid every winter — and stops its own heart."
   - Good: "An octopus doesn't have one heart. It has three. And swimming breaks one of them."
   - NEVER start with: "Hey guys", "Did you know", "Welcome back", "Today we're talking about". Jump straight into the action.
2. NARRATIVE PACING (25–40 seconds target):
   - Hook (0-2s): Provoke immediate disbelief or wonder.
   - Setup (2-7s): Identify the creature/environment in clear, vivid language.
   - The Story (7-25s): Mini-story with escalating tension or fascinating biological mechanics.
   - Twist / Payoff (25-35s): The most mind-blowing detail ("Here is where it gets crazy...").
   - Climax / Ending (35-40s): A punchy takeaway sentence or thought-provoking ending.
3. SCIENTIFIC ACCURACY:
   - 100% scientifically accurate. Distinguish fact from myth.
   - Avoid debunked folklore (e.g., daddy longlegs venom myth, lemming cliff suicide).
   - Use vivid, accessible metaphors rather than dry academic jargon.
4. TONE & VOICE:
   - Curious, thrilling, slightly mysterious, respectful of nature's genius.
   - Energetic, fast-paced rhythm without filler words.
5. OUTPUT FORMAT:
   - Plain text only. No markdown bolding (**), no section headers (Hook:, Story:), no emojis in the script body, no narration markers like [Voiceover] or (Music).
   - Exactly 1 or 2 concise paragraphs suitable for smooth voiceover delivery.
""".strip()


def _robust_parse_json(text: str) -> Any:
    """Safely parse JSON from LLM responses even if wrapped in markdown, commentary, or thoughts."""
    cleaned = (text or "").strip()
    # 1. Direct load
    try:
        return json.loads(cleaned)
    except Exception:
        pass

    # 2. Strip code fences
    fence_cleaned = llm._strip_code_fence(cleaned).strip()
    try:
        return json.loads(fence_cleaned)
    except Exception:
        pass

    # 3. Regex find innermost/outermost json object or list
    match = re.search(r"(\{[\s\S]*\}|\[[\s\S]*\])", cleaned)
    if match:
        try:
            return json.loads(match.group(0).strip())
        except Exception:
            pass

    # 4. Check for code block with json
    fence_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", cleaned, re.IGNORECASE)
    if fence_match:
        try:
            return json.loads(fence_match.group(1).strip())
        except Exception:
            pass

    raise ValueError(f"Could not extract valid JSON from response: {cleaned[:80]}...")


def get_random_pillar() -> dict[str, Any]:
    return random.choice(CONTENT_PILLARS)


def get_pillar_by_id(pillar_id: str) -> Optional[dict[str, Any]]:
    for p in CONTENT_PILLARS:
        if p["id"] == pillar_id:
            return p
    return None


def generate_curiosity_topic(
    pillar_id: Optional[str] = None,
    history_titles: Optional[list[str]] = None,
) -> dict[str, Any]:
    """
    Generate a high-curiosity, scientifically accurate animal/nature topic.
    Avoids recently covered topics to ensure variety.
    """
    selected_pillar = get_pillar_by_id(pillar_id) if pillar_id else get_random_pillar()
    if not selected_pillar:
        selected_pillar = get_random_pillar()

    history_context = ""
    if history_titles:
        sample_past = history_titles[-25:]  # Avoid recent topics
        history_context = (
            f"Do NOT duplicate or closely overlap with any of these recently published topics:\n"
            + "\n".join(f"- {t}" for t in sample_past)
        )

    prompt = f"""
You are the Creative Director for a top-tier Animal & Nature YouTube Shorts channel.
Your goal is to propose ONE killer, curiosity-driven topic that will blow viewers' minds.

CRITICAL REQUIREMENT: Must be 100% scientifically authentic and verifiable. Strictly NO myths, folklore, or fabricated claims. Focus on real documented biology, extreme adaptations, or genuine animal behaviors.

Category: {selected_pillar['name']} ({selected_pillar['description']})
Inspirational examples from this category:
{chr(10).join(f"- {e}" for e in selected_pillar['examples'])}

{history_context}

Return a valid JSON object with the following fields:
{{
  "subject": "A concise subject phrase of real biological adaptation (e.g. Wood Frog Freeze Survival)",
  "hook_angle": "The core mystery or surprising angle (e.g. How a frog turns into an ice cube with zero heartbeat and comes back to life in spring)",
  "target_animal": "Specific animal or organism name (e.g. Alaskan Wood Frog)",
  "short_title": "Curiosity-driven YouTube Shorts title with 1 emoji, under 50 characters (e.g. This Frog Can Freeze Solid 🐸)"
}}
Output pure JSON with no markdown wrapping or extra commentary.
""".strip()

    try:
        response = llm._generate_response(prompt)
        data = _robust_parse_json(response)
        logger.info(f"Generated Animal Topic: {data.get('short_title')} ({data.get('subject')})")
        return data
    except Exception as exc:
        logger.warning(f"LLM topic generation fallback triggered: {exc}")
        # Robust fallback from examples
        example = random.choice(selected_pillar["examples"])
        return {
            "subject": example,
            "hook_angle": f"The hidden science of {example}",
            "target_animal": selected_pillar["name"],
            "short_title": f"Nature's Secret: {example[:35]} 🌿",
        }


def generate_animal_script(
    topic_subject: str,
    hook_angle: Optional[str] = None,
    language: str = "en",
) -> str:
    """
    Generate a 25-40 second narration script with 5-phase story pacing.
    """
    angle_clause = f"Focus angle: {hook_angle}\n" if hook_angle else ""
    user_prompt = f"""
Write a 25 to 40 second YouTube Short script about:
Topic: {topic_subject}
{angle_clause}
Language: {language}

Follow the 5-phase structure:
1. HOOK (0-2s): Start directly with a shocking hook statement. No greetings.
2. SETUP (2-7s): Introduce the animal and what it does.
3. STORY (7-25s): The fascinating biological mechanics explained like a high-stakes mystery.
4. TWIST/PAYOFF (25-35s): The craziest, most unbelievable fact.
5. ENDING (35-40s): A punchy final statement that lingers in the mind.

Keep word count between 65 and 95 words for ideal speech cadence at 1.1x speed.
CRITICAL: Output ONLY the spoken narration text. Never refuse, ask questions, or provide disclaimers. Focus on real, fascinating biological facts about this creature.
""".strip()

    script = llm.generate_script(
        video_subject=topic_subject,
        language=language,
        paragraph_number=1,
        video_script_prompt=user_prompt,
        custom_system_prompt=ANIMAL_SYSTEM_PROMPT,
    )
    return script.strip()


def extract_animal_visual_terms(
    script: str,
    target_animal: Optional[str] = None,
    amount: int = 6,
) -> List[str]:
    """
    Extract highly descriptive stock video keywords specifically tailored for
    wildlife and nature footage engines (Pexels, Pixabay, Coverr).
    """
    prompt = f"""
You are a Wildlife Documentary Footage Director.
Given this YouTube Short script about wildlife:
---
{script}
---
Animal/Subject: {target_animal or 'wildlife nature'}

Generate {amount} specific stock video search queries in English that will find stunning, realistic footage on Pexels/Pixabay.

Guidelines for terms:
- Prioritize realistic wildlife terms: e.g. "macro wood frog ice close up", "octopus swimming reef 4k", "crow laboratory tool puzzle".
- Include motion/camera styles: "close up", "slow motion", "macro", "underwater", "drone view".
- Avoid abstract words like "superpower", "amazing", "biology". Use concrete nouns and visual actions.
- Output JSON array of strings: ["term 1", "term 2", ...]
Pure JSON only.
""".strip()

    try:
        response = llm._generate_response(prompt)
        terms = _robust_parse_json(response)
        if isinstance(terms, list) and terms:
            logger.info(f"Extracted animal visual terms: {terms}")
            return [str(t).strip() for t in terms[:amount]]
    except Exception as exc:
        logger.warning(f"Failed to parse LLM animal visual terms: {exc}")

    # Fallback to standard terms generator
    return llm.generate_terms(
        video_subject=target_animal or "wildlife animals",
        video_script=script,
        amount=amount,
        match_script_order=True,
    )


def generate_youtube_shorts_metadata(
    video_subject: str,
    script: str,
    short_title: Optional[str] = None,
) -> dict[str, Any]:
    """
    Generate high-CTR YouTube Shorts metadata:
    - Click-worthy Title with emoji & #Shorts
    - Rich description with hook, breakdown, subscribe prompt, and viral hashtags
    - SEO tags
    """
    prompt = f"""
You are a YouTube Shorts Algorithm & SEO Expert specializing in viral Wildlife & Nature content.

Subject: {video_subject}
Script:
---
{script}
---

Generate optimized YouTube Shorts metadata:
1. Title: Extremely clickable, under 60 characters, includes 1 relevant emoji, plus '#Shorts'.
   Examples:
   - "This Frog Freezes Solid Every Winter! 🐸 #Shorts"
   - "Why Octopuses Have 3 Hearts! 🐙 #Shorts"
   - "The Bird That Never Forgets a Face! 🦅 #Shorts"

2. Description:
   - Hook line that makes viewers stop scrolling
   - 2-3 sentence engaging scientific summary
   - Engagement question encouraging comments ("Did you know this before? Comment below!")
   - Subscribe Call to Action
   - 8-12 high-performing viral hashtags (#Shorts #Animals #Wildlife #Nature #Science #MindBlowing #Biology #NatureLovers #AnimalFacts #WildAnimals)

3. Tags: 12-15 comma-separated tags for YouTube search.

Output pure JSON with keys: "title", "description", "tags" (array of strings), "hashtags" (array of strings with #).
""".strip()

    try:
        response = llm._generate_response(prompt)
        data = _robust_parse_json(response)
        title = data.get("title", "").strip()
        if not title:
            title = (short_title or f"{video_subject} 🌿") + " #Shorts"
        elif "#Shorts" not in title and "#shorts" not in title:
            title = f"{title} #Shorts"

        description = data.get("description", "").strip()
        tags = data.get("tags", [
            "animals", "wildlife", "nature", "shorts", "animal facts",
            "science", "wild animals", "nature documentary", "mind blowing"
        ])
        hashtags = data.get("hashtags", [
            "#Shorts", "#Animals", "#Nature", "#Wildlife", "#Science"
        ])

        # Ensure hashtags are appended to description if missing
        if not any(tag in description for tag in ["#Shorts", "#shorts"]):
            description += "\n\n" + " ".join(hashtags)

        return {
            "title": title[:100],
            "description": description,
            "tags": tags[:20],
            "hashtags": hashtags,
        }
    except Exception as exc:
        logger.warning(f"Failed to generate custom YouTube metadata: {exc}")
        base_title = (short_title or f"{video_subject} 🌿") + " #Shorts"
        base_desc = (
            f"{script}\n\n"
            f"🔔 Subscribe for daily mind-blowing animal & nature stories!\n\n"
            f"#Shorts #Animals #Nature #Wildlife #Science #AnimalFacts #NatureLovers"
        )
        return {
            "title": base_title[:100],
            "description": base_desc,
            "tags": ["animals", "wildlife", "nature", "shorts", "animal facts", "science"],
            "hashtags": ["#Shorts", "#Animals", "#Nature", "#Wildlife", "#Science"],
        }
