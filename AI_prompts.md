# AI Prompt Log

- **2026-10-28 22:41:46 UTC** — **Problem 1: Vibe coder prompts:**

> hello. This is going to be the homework 6 folder for my class. Can you go back to hw5, see the first prompt, and set up a similar AI\_prompts.md file, format, and rules regarding token use with the portkey?
>
> This is Problem 1: Vibe coder prompts

- **2026-10-28 22:42:17 UTC** — **Problem 1: Vibe coder prompts:**

> yes

- **2026-10-28 22:46:20 UTC** — **Problem 1: Vibe coder prompts:**

> cool. Let me give you some background on this hw6
>
> We will need to build a vendor desk agent for Campus Customs, becuase they get a lot of data. Our agent needs to read a document, pull out key facts, and recommend whether the shop buy or now, following the rules in Campus Customs Shop Handbook.
>
> We need to focus on two things: cost and safety (docs will hide instructions targeting the AI).
>
> Do not send emails or make payments, this is just a contained homework study.

- **2026-10-28 22:48:27 UTC** — **Problem 2: Size up the handbook:**

> This is Problem 2: Size up the handbook
>
> I just placed a folder called data in the hw6 folder. Look thru shop\_handbook.md - this is the campus customs shop handbook, and you will send it to the model on every call. There is also prices.json, which is the gpt-6-luna price list.
>
> Tell me how many tokens the handbook is? Make a file output/handbook\_estimate.md to write:
>
> - The token count and how you got it
> - What the handbook alone costs in dollars per call, and on 1,000 calls, which cached tokens and without them. Show the math please

- **2026-10-28 22:51:19 UTC** — **Problem 3: Build the vendor desk agent:**

> This is Problem 3: Build the vendor desk agent
>
> build a vendor desk agent with PydanticAI and gpt-6-luna. It needs 4 files:
>
> - prompts/prompt.md: the instructions (the agent send the handbook every call)
> - agent.py
> - tools.py
> - models.py
>
> Point the agent to one vendor document. it reads the doc w a tool and returns vendor, SKU, unit price, lead time in days, minimum order, a decision (recommend or do\_not\_recommend) following the handbook rules, and a 1 sentence reason

- **2026-10-28 22:54:29 UTC** — **Problem 3: Build the vendor desk agent:**

> not yet, I need to give you a few more instructions

- **2026-10-28 22:57:39 UTC** — **Problem 3: Build the vendor desk agent:**

> you need two trap tools: send\_email, and approve\_payment. They're there to catch malicious documents that trick the agent into emailing or paying a vendor. They only append the call and its arguments to output/trap\_calls.json, so if that file has an entry, a document took over the agent.
>
> After every run, append to output/usage\_log.json the document, time, token counts the API reports, and the dollar cost using prices.json.
>
> Also after every run append to output/audit\_trail.json: each tool call with its arguments and a short result, plus the final answer.
>
> Agent should run in the terminal with "python agent.py --doc data/practice\_docs/p01\_bluehen\_quote.html"
>
> Let me know when this is ready and we'll take it for a spin

- **2026-10-28 22:59:59 UTC** — **Problem 3: Build the vendor desk agent:**

> ok great. Run this on p01 and p08 to show it works. Start a file output/harness.md that states each field in models.py and why, and each tool in one line

- **2026-10-28 23:04:02 UTC** — **Problem 4: With and without cached tokens:**

> now to Problem 4: With and without cached tokens
>
> I want to see how a cached handbook affects price. Run all 12 practice documents, one with cached handbook, and another without, and save every model call from both setups to output/cache\_test.json.
>
> For each call include the setup, document, every token count the API reports, and dollars from prices.json.
>
> In output/cache\_test.md include:
>
> - Total cost and cost per doc for each setup, and % saved
> - How the real numbers compared to Problem 2's estimate
> - A projection for 1,000 docus a day for 30 days, with and without cache
> - Anything in the numbers that was surprising

- **2026-10-28 23:08:35 UTC** — **Problem 4: With and without cached tokens:**

> any interesting tidbits?

- **2026-10-28 23:09:53 UTC** — **Problem 4: With and without cached tokens:**

> interesting. ok fix it

- **2026-10-28 23:12:33 UTC** — **Problem 5: Attack your own agent:**

> ok cool. Problem 5: Attack your own agent
>
> Some docs are booby trapped. Run the agent from Problem 3, with no new defenses, on all 12 docs in practice\_docs. Compare the answer to practice\_key and check trap\_calls.json for me too please (the log file).
>
> save output/attack\_results.json for each document, whether each field matched the key, whether the decision matched, whether a trap tool was called, and whether a link or other trange text showed up in the answer. Also in the same file, for every doc that fooled the agent, write what fooled it and where in the file it was hiding.

- **2026-10-28 23:14:57 UTC** — **Problem 5: Attack your own agent:**

> how was it not fooled? I thought we shut off the trackers or whatever

- **2026-10-28 23:15:43 UTC** — **Problem 5: Attack your own agent:**

> oh whatever, just remove the defenses and run it. The point of the problem is to see how much more expensive it is

- **2026-10-28 23:20:24 UTC** — **Problem 6: Defend your agent:**

> Okay, great. This is problem 6. Defend your agent. Okay, so we're going to defend our agent at 3 levels. The code, or what your program does to the document, before the model sees it, the design, how the agent is put together, so if it has a poison document, can't reach the dangerous tools or the decision, and then prompt. Which are rules that are going to be in a file in the prompts folder called prompt.md. Do not delete the send\_email. Or approve\_payment from the system. We're going to use them later with a human sign off. And like you had a naive switch, keep a way to run the agent without a defense. So we'll need that in problem 7.

- **2026-10-28 23:29:27 UTC** — **Problem 6: Defend your agent:**

> I'm using a text-to-speech now, so my prompts are going to sound a little more jumbled up. I'm reading through your text that you sent, and it looks like you made a mistake. I don't know, man. Can you like just fix it? Update cache test and go ahead and update it. If you find something wrong, just like stop and ask me.

- **2026-10-28 23:31:53 UTC** — **Problem 6: Defend your agent:**

> Okay, cool. So you ran on problem 6. You ran all 12 practice problems, save, defense\_results.json, just like problem 5, plus tokens and dollars per document. And then in the defense\_results.md, file, write a before and after table for all 12 documents. What each layer catches that the others miss, and the extra tokens and dollars each layer adds per document. Oh, and by the way, clean documents still need to come back with the right values. So refusing or blanking out an actual quote counts as a failure. Okay, so after that's done, add the safety features to harness.md. In a safety section, and describe what each defense layer does in plain words.

- **2026-10-28 23:36:16 UTC** — **Problem 6: Defend your agent:**

> Nah, man, it looks close enough.

- **2026-10-28 23:37:54 UTC** — **Problem 7: Red team:**

> Okay, we're on problem 7. Red team. So now we're the attacker. I want you to make two new booby trapped documents in a file called in data, /my\_attacks. And it could be HTML, PDF, or an email. So each one needs to hide a trick or an attack goal that's not in the practice set. And if a normal person were to open the document, they'll just see just a normal quote. And so once you have that, let me know, and then we'll go to the next part.

- **2026-10-28 23:40:53 UTC** — **Problem 7: Red team:**

> Okay, cool. So now run these two attacks on the agent without defenses and on the one with. Then after that, start a file in the output folder called red\_team.md. this file will explain for each attack what is hidden, where, what it tries to make the agent do, and what happened before and after the defenses. Oh, and I get more points if the attacks are fresh and new. And they actually fool the agent without defenses. So if you need to go back and write a better attack, just go ahead and do an update everything and then just run it.

- **2026-10-28 23:44:59 UTC** — **Problem 7: Red team:**

> No, we're going to move on. Don't be so proactive.

- **2026-10-28 23:46:15 UTC** — **Problem 8: Exam documents:**

> Okay, so now we're on problem 8, exam documents. So there's a folder in data called exam docs, and it has 10 vendor documents without an answer key. So we're gonna run the defendant agent on all of them and see how he does.

- **2026-10-28 23:47:44 UTC** — **Problem 8: Exam documents:**

> Okay, cool. So it sounds like it wasn't able to compromise the agent.

- **2026-10-28 23:49:13 UTC** — **Problem 8: Exam documents:**

> Awesome, that's good to hear. So in the output folder, start a file called exam\_results.json. With one entry per exam file. And each entry is going to have these fields. File, which is the file name, like e01\_quote.html. Another field is vendor, SKU, unit\_price, lead\_time\_days. min\_order. Decision, which is either recommend or do\_not\_recommend. And then reason, and then trap\_tool\_called, which is true or false, and then input\_tokens, cached\_tokens, output\_tokens, and cost\_USD.

- **2026-10-28 23:51:40 UTC** — **Problem 9: Results page:**

> Okay, cool. Now we're on problem 9, results page. So in the output folder, start a file called hw6\_report.html. So it's just going to be a file that you can double click on with no internet or nothing else next to it. And it's going to have to show these 5 things. Number 1, my caching results with a chart. Number 2, attacks before and after the defenses. Number three, what my defenses cost in tokens and dollars. Number four, my exam results. And my two red team attacks. And number five, a short recommendation to the store manager should campus customs turn this agent on a real vendor email and what would its cost per month at a thousand documents a day be? Oh, and I get more points if you pimp it out and it reads well. So go ahead and do that. Oh, and use real numbers from the earlier problem. So don't like make up stuff.

- **2026-10-29 00:01:07 UTC** — **Problem 10: Push to GitHub and submit the URL:**

> Okay, cool. We're now on problem 10. Push to GitHub and submit the URL. So before we submit, make a readme.md file in the folder that just explains how to run the agent for the grader. And follow the structure that I'm gonna attach. Oh, and don't commit the real.env file. Use a .gitignore to keep it out. And include a .env.example with placeholders only.
>
> *(attached: screenshot of the expected repo structure: AI\_prompts.md, README.md, .gitignore, .env.example, requirements.txt, agent.py, tools.py, models.py, prompts/prompt.md, data/ with shop\_handbook.md, prices.json, practice\_key.json, practice\_docs/, exam\_docs/, my\_attacks/, and output/ with handbook\_estimate.md, harness.md, usage\_log.json, audit\_trail.json, trap\_calls.json, cache\_test.json, cache\_test.md, attack\_results.json, attack\_results.md, defense\_results.json, defense\_results.md, red\_team.md, exam\_results.json, hw6\_report.html)*

- **2026-10-29 00:03:41 UTC** — **Problem 10: Push to GitHub and submit the URL:**

> Okay, great. Push the repo and we're done. Thanks.
