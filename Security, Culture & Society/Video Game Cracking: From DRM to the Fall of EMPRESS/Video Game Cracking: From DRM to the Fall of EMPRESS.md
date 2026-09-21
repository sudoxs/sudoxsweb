# Video Game Cracking: From DRM to the Fall of EMPRESS
## An Analysis of Economics, Technique, and Ethics in the Software Underground

---

## Introduction: Why Cracking a Game Is Different from Cracking a Movie or Song

The common perception is that cracking a video game is just like copying a movie or a song — you take a file, break its lock, and distribute it. But the reality is that video games present one of the most complex reverse-engineering challenges in software.

Why? Because unlike movies and music, which are linear content, a video game is **a running piece of software**. Developers can obfuscate its code, constantly verify whether the user is authorized, and even keep parts of the game logic on a server. This means cracking a game is not merely removing a simple check — it is a **multi-layered technical battle** between the development team and the cracking team.

---

## Part One: What Is DRM and How Does It Work?

**DRM**, or **Digital Rights Management**, is a set of technologies designed to prevent unauthorized copying and modification of software. In gaming, DRM typically has several layers:

**1. Authentication Layer**
The game checks whether you have a license before running. This can be done through:
- **Online check**: connecting to the developer's server and validating a license key
- **Offline check**: a local file or registry entry that confirms purchase
- **Hardware check**: binding the license to your hardware specifications (e.g., CPU ID or hard drive)

**2. Anti-Tamper Layer**
This layer ensures the game code **has not been modified**. If a cracker tries to remove a check or alter the code, this layer detects it and crashes the game.

**3. Obfuscation Layer**
The game code is made so complex that reading it is nearly impossible for a human. Variables get meaningless names, program logic is scattered across thousands of nested functions, and static analysis becomes practically paralyzed.

**4. Timing Checks**
The game constantly verifies whether the code has been tampered with. For example, if a specific function executes faster or slower than normal, it means something has been altered.

---

## Part Two: How Crackers Bypass These Layers

Cracking a game usually involves several stages:

**Stage One: Static Analysis**
The cracker opens the game's executable and reads its assembly code. Tools like **IDA Pro** and **Ghidra** allow them to see the program structure, locate important functions, and understand where the authentication logic resides. But if the code is obfuscated, this stage can take weeks.

**Stage Two: Dynamic Analysis**
The cracker examines the game **while it is running**. Using tools like **x64dbg** and **OllyDbg**, they read the program's memory, trace registers, and observe the decisions the code makes at runtime. This stage is usually more effective than static analysis because it shows the actual behavior of the program.

**Stage Three: Finding the Decision Point**
The cracker must find where the game decides "user is authorized" or "not." This point is usually a simple condition — for example, an `if` statement that, if true, lets the game run.

**Stage Four: Patching**
The cracker manipulates that condition — reverses its logic or removes it entirely. But if the game has an anti-tamper layer, this patch is detected and the game crashes.

**Stage Five: Server Emulation**
If the game connects to an online server, the cracker must build a **fake server** that returns the correct responses. This requires a detailed understanding of the game's communication protocol.

**Stage Six: Distribution**
Once the crack is ready, the cracker releases a **patched executable** or a **separate crack**. The user must download the original game and then apply the crack.

---

## Part Three: History of Game Cracking — From DOS to Denuvo

**1980s and 1990s: The Golden Age of Simple Cracks**
During this period, games were released on floppy disks or CDs, and DRM was virtually non-existent. Cracking a game meant removing a simple check that asked "Is the original disk in the drive?" Tools like **CORE** and **Razor 1911** emerged, and cracks were usually distributed as a **small crack file** (e.g., a `crack.exe`).

**2000s: The Rise of Advanced DRM**
With the arrival of **SecuROM** and **SafeDisc**, cracking became harder. These DRMs used **hardware checks** and **code obfuscation**. Groups like **RELOADED**, **SKIDROW**, and **Razor1911** were challenged, and new techniques such as **emulation** and **virtual drives** became common.

**2010s: The Era of Steam and Online**
With the rise of **Steam**, digital games became mainstream, and online DRMs (like **Steamworks**) entered the scene. Cracking these required full emulation of the Steam server. Teams like **REVOLT**, **CPY**, and **CODEX** excelled during this period.

**2014 Onward: The Arrival of Denuvo**
This was the turning point for game cracking. **Denuvo** was an Austrian DRM that combined several advanced techniques:
- **Virtual machine (VM)**: game code runs inside a virtual environment, making analysis extremely difficult
- **Dynamic checks**: constantly verifies that code has not been tampered with
- **Heavy obfuscation**: functions and variables are so complex that even static analysis barely works

Denuvo was so effective that in its first year (2014–2015), only **six games** using it were cracked. This number, compared to hundreds of games cracked in the same period without Denuvo, shows its immense impact.

---

## Part Four: The EMPRESS Phenomenon — Hero or Opportunist?

### The Rise of an Independent Cracker

**EMPRESS** is the alias of a cracker known in the game-cracking world as **the only individual who can break Denuvo alone**. Before EMPRESS, cracking Denuvo was almost always the work of **multi-person teams** — because coordinating static analysis, dynamic analysis, patching, and testing required significant manpower.

EMPRESS had been active in hacker groups from the start, but her name spread when she **single-handedly** cracked **Planet Zoo**. This success drew the community's attention, and afterward, major games were cracked by EMPRESS one by one.

### Why Did EMPRESS Succeed?

Several factors set EMPRESS apart:

**1. Working Independently**
EMPRESS was not part of any large group and worked alone. This meant **faster decision-making**, but also **a heavier workload** on one person.

**2. Quality of Cracks**
EMPRESS's cracks not only bypassed Denuvo but were sometimes **better than the original version**. For example, in **Resident Evil Village**, her crack not only removed the lock but also fixed performance issues in the original — such as improved frame rate and reduced size.

**3. Controversial Personality**
EMPRESS was a **charismatic and controversial** figure. On one hand, the gaming community (especially in developing countries) saw her as a **hero** standing up to gaming industry giants. On the other hand, her strange behavior and controversial statements made her many enemies.

### The Turning Point: The Wired Interview

In a rare interview with **Wired**, EMPRESS presented herself as someone whose **goal was not money, but fighting the system**. She said:

> "I have a goal that no one else has. I have no need for pride."

This interview made EMPRESS known as a **revolutionary figure** — someone single-handedly fighting multi-billion-dollar companies.

---

## Part Five: The Fall of EMPRESS — From Hero to Outcast

### 1. Breaking the Donation Taboo

In the cracking community, there is an **unwritten rule**: **cracks must be free**. Crackers work for **fame and competition**, not money. Some groups even explicitly state in their crack files that "we do this for free."

EMPRESS broke this taboo and **started accepting donations**. This move caused many other crackers to see her as a **traitor to the cracking philosophy**.

### 2. Holding Files Hostage

Worse than donations was **holding files hostage**. EMPRESS would **keep crack files for certain games to herself** and say she would not release them until a certain amount of money was donated. Even after the money was raised, she **deliberately slowed download speeds** and said more money was needed for faster speeds.

This directly hurt **low-income gamers** — the very people who, due to sanctions or high prices, had no choice but to crack.

### 3. Being Ostracized by FitGirl

**FitGirl** was one of the most famous **repackers** (people who compress game files to reduce size and make downloading easier). FitGirl announced that she would **no longer repack any EMPRESS cracks**. This meant EMPRESS's cracks no longer reached a large part of the community.

### 4. Arrest

Eventually, **EMPRESS's identity was exposed**. According to her own post on Reddit, **haters and FitGirl found her address and reported her to the police**. EMPRESS said in a post that "in less than an hour, she and her lawyer would go to the police."

Some time later, EMPRESS returned and said she had been **released thanks to her lawyer**. But this incident clearly showed that **asking for money and holding files hostage created a huge legal risk**.

### 5. Racist Remarks

After returning, EMPRESS **apologized** to the community and was given **a second chance**. But that chance did not last long. EMPRESS wrote a **anti-Indian** post saying she **hated Indians** and would not even talk to anyone from India.

This remark caused **a large portion of her fans to turn against her** — because India, with over a billion people, makes up a large part of the gaming and cracking community. Yet many still tolerated EMPRESS, because **they didn't care what she thought — all that mattered was free games**.

---

## Part Six: Lessons and Analysis

### 1. The Contradiction Between Hacker Ethics and Personal Capitalism

The EMPRESS story reveals a **fundamental contradiction**: the cracking community is built on the **philosophy of free information**. Crackers work for **fame and challenge**, not money. When EMPRESS started **making money**, she effectively acted against the very philosophy she claimed to represent.

### 2. The Dangers of Losing Anonymity

Crackers usually work **anonymously** because their work is **illegal**. When EMPRESS began **public interaction** with the community, **media interviews**, and **accepting donations**, she effectively **exposed her identity to danger**. This not only created **legal risk** but also **many enemies**.

### 3. The Power of the Community

The EMPRESS story shows that the **cracking community** is a **living entity** that can **lift someone up** or **crush them**. EMPRESS was initially popular for her **technical skill** and **independent work**, but when she **acted against community values** (money, hostage-taking, racism), the community quickly **turned against her**.

### 4. Impact on the Security Industry

The EMPRESS story offers several lessons for those working in **cybersecurity**:
- **DRM and anti-tamper** are always an **arms race** — every lock will eventually be broken
- **Reverse engineering** is a **double-edged skill** — it can be used for **security research** or **circumventing laws**
- **Financial motivation** can drag even **the most skilled individuals** into **downfall**

---

## Conclusion

EMPRESS was a **unique phenomenon** in the game-cracking world — someone who single-handedly broke a powerful DRM and became a **legend**. But her fall was equally **dramatic**.

The EMPRESS story shows that **technical skill** alone is not enough. **Ethics**, **philosophy**, and **respect for the community** matter just as much. And perhaps most importantly, it shows that in the software underground, **fame** can be both **your best friend** and **your worst enemy**.
