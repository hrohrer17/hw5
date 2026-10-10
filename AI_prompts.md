# HW5 — AI Prompts Log

This is the log of what I typed to my vibe coder (Claude Code) for Homework 5, kept up to date as
I work. Prompts are copied word for word.

**Note on AI use:** I used Claude Code to build and draft from my prompts, and to check my finished work against the assignment page.

---

## Getting started (before Problem 1)

**Prompt 1 (scenario overview + data setup):**

> All right, so for homework number five, the scenario is that we're building a campus customs multi-agent um, operation. So it's going to be a team. And they're going to run the shop. So they'll handle things like tickets. Like customer orders, rent, unpaid bills, discount requests. Anything in the shop has to handle or deal with. We need three pieces that talk to each other. So an MCP server, a fast API backend, with a multi-agent team and a React dashboard. So that a human can watch the agents at work and approve the requests. It's important that the team has full connectivity so like any agent can delegate tasks to another agent for help and the agents are as follows a boss who reads each ticket and decides who should work on it and the boss makes the final calls an inventory agent that checks stock by SKU and size spots shortfalls and figures out which vendor can restock An accounting agent that watches cash and invoices, checks the margins and prepares payments or purchase orders for human approval. Then a facilities agent that handles the shop space side. So the leases and the rent and other things of that nature. And then a customer service agent who drafts messages for customers. I've downloaded the data.zip it's in my downloads folder so I want you to open that up and actually move it to the appropriate folder for this homework tool should update the database as the ticket gets resolved and I want a copy of the database file called data forward slash campus underscore customs underscore new dot db and point the MCP server and backend at that working copy. I want the campus underscore customs dot db untouched. So you can reset when you want to restart resolving the tickets. Some rules of this shop. The field desk.date underscore today is today. For the shop. So use this date to determine what is overdue and what's been submitted in the past. The next rule, a vendor lead time comes from the vendor's table. A vendor will not ship new product while they still have an open unpaid invoice. Human approval is required for any payments. And this is incredibly important. If a payment is made, make sure to update the relevant table. There's not enough cash to pay tool must refuse. So no negative balances for this. We're only going to do cash going out for this homework. No money will come in. Because we haven't modeled revenue. Before we execute a full run to resolve the tickets, make sure to reset the database to the original values. And do not email customers or call real vendors. Drafts down the board. We use the port key API key for AI calls. And for this assignment, only use GPT-6 Luna through port key for every agent. Multi-agent chats are going to cost a lot more money than we have. So points will be deducted if we use anything other than GPT-6 Luna for the agents. Okay, it's come up again. To not paste the page URL and do not screenshot the problems to finish everything. Do you think that because I'm not using the URL to do everything, and to not finish everything, I'm just using it as a final check, it's okay? After we talk through this, we'll do problem one.

**Prompt 2 (AI-use note):**

> Okay. Remind me to add that one line note to the prompt log. Unless I can do it now. Which add it to the log, like you used AI to check my finished work against the assignment page.

---

## Problem 1: Vibe coder prompts

**Prompt:**

> Okay, prompt or problem number one. So create AI_prompts.md at the start of this assignment and keep it updated as we go. The file is a log of what I've typed to you. Put one section for each problem and each section must include the problem number and title, at least one prompt you typed, well, okay, scratch that, at least one prompt that I typed, and then a follow-up prompt that I used if I needed it. Add a one sentence on what was lacking after the first prompt.

**Follow-up prompt:** None needed.

---

## Problem 2: Study the Campus Customs database

**Prompt:**

> Open data/campus_custom.db and scan everything. Copy the original file to data/campus_customs_new.db - later problems will update that working copy. Study the 3 open tickets and tell me how they link to other tables. Start output/harness.md . For each table, list the fields and one short line on why that table matters, on why that table matters for the agents that we're working with. The harness file will grow as we go.

**Follow-up prompt:** None needed.

---

## Problem 3: Build the MCP server

**Prompt:**

> For problem 3: After that, build an MCP server in MCP underscore server forward slash using fast MCP. It will talk to data forward slash campus underscore customs underscore new dot db. We don't need to connect it or run it. In this problem. So we're going to be using tools in the MCP server, and we're going to add more tools later. But for now, give me three tools I know that I'm going to need for the tickets in the database. Make the names clear and don't invent any kind of data. Only use information in the database. In output/harness.md List each of the three MCP tools and for every tool include which table it reads, which ticket it helps unlock, so it could be 101, 102, or 103, and add one sentence on why that tool is the right one for that ticket. Make the lines very specific. Anything vague, like it quote reads inventory quote, won't be good enough. Tie the tool to the ticket. Also, add a short mcp_sever/readme/md file that explains what the MCP server is for. Which database file it uses, and the three tools it has. Again, make this specific. Keep it short, but make it specific and not vague.

**Follow-up prompt:** None needed.

---

## Problem 4: Add the MCP server to the vibe coder and test each tool

**Prompt:**

> All right, problem number four, we're going to add the MCP server to Vibe Coder and test each tool. So add the MCP server to this project. So the Vibe Coder can call the tools. Save the connection JSON text in .mcp.json at the project root. Or however you saved the local MPC server list. Once the vibe coder is connected, test each of the three MCP tools. Save the evidence in output/mcp_smoke.json . For every tool, include the prompt that I asked the tool name and the tool output, which must match values in data/campus_customs_new.db . so the Vibe Coder can call the tools. Save the connection JSON text in. at the project root, or however you saved the local MPC server list. Once the vibe coder is connected, test each of the three MCP tools. Save the evidence in. For every tool, include the prompt that I asked, the tool name, and the tool output, which must match values.

**Follow-up prompt** (sent between setup and tests, after Claude suggested running the tests in a new session):

> I don't think this is what the homework had in mind. I need it to be all one session so that the log and other files are or have continuity. I think the way we've been doing it is fine.

**What was lacking after the first prompt:** The first attempt would have tested the tools in a separate new session, which broke the one-session continuity of this log, so the follow-up kept everything in this session (the app was restarted so this session could load the server).

**Test prompts (asked once the server was connected):**

> What is the price of a hoodie? Who is our favorite vendor? How much is our lease per month?

---

## Problem 5: Build the agent team and grow the MCP tools

**Prompt:**

> Problem 5 All right, build the agentic team for campus customs using Pydantic AI: Boss inventory accounting facilities and customer service. Include prompts, models, and agent loops so they can delegate work to each other and assign work to each other with full connectivity. Put the agent prompts in backend forward slash prompts forward slash and make sure it's one file per agent. Put the data types in backend forward slash models.py and the agent files under backend forward slash. A layout can vary as long as the five rules are clear. Use Porykey_API_key and ONLY gpt-6-luna for every agent. Write each prompt in your own words with the shop rules that agent needs. And the more detailed prompts that cover all aspects of an agent's work and scope, are desired. We don't want short or generic prompts. So make them detailed. Also for problem five, add any tools the agents need to the MCP server so they can work on the open tickets shop facts come from the MCP server over data/campus_customs_new.db - Don't invent a second shop tools layer that bypasses MCP. Wire the agents so they append to output forward slash audit underscore trail dot JSON As they run: I want you to record enough data from each agent loop step to audit it later. Append to this file and do not wipe it each run. In output forward slash harness dot md, list each agent and each MCP tool. including the ones that we're adding in this problem. Along with which table the tool uses. Also add a short safety section so talk about the guardrails of real business would want. When agents touch real customers and real money and also limits that keep token use in check. Then update MCP underscore server forward slash readme dot md so the tool list matches what we have now.

**Follow-up prompt:** None needed.

---

## Problem 6: Plan the three tickets

**Prompt:**

> All right, problem six. We're going to plan the three tickets. So before you wire the back end, write down your expectations for the team for each open ticket. So build output forward slash desk underscore tickets.html. And make sure it's a page you can double click with one tap per ticket. So ticket 101, ticket 102, and ticket 103. Also add empty cache and reflection tabs for every problem after this. Leave them blank or with a short "Coming later" note for now. And add an exclamation point at the end of coming later. So that people can tell we're enthusiastic about our website. Then on each ticket tab, fill in expected section only. Make sure you leave room for an actual section and we're gonna fill that in after we run the agents.

**Follow-up prompt:**

> Also for problem six. For each ticket's expected section, write who the boss should call first and why. All the agent delegations you expect. So not that you know the boss calls everyone. And then which MCP tools you expect that run to use. We don't want every specialist to get sent on every ticket. Because it's a waste of time and efficiency. Then once we make this plan, we'll compare it with what actually happens when the agents do resolve the three tickets.

**What was lacking after the first prompt:** The first prompt didn't say what each Expected section had to contain, so the follow-up spelled it out: who the Boss calls first and why, every delegation we expect (not "Boss calls everyone"), and which MCP tools we expect.

---

## Problem 7: Backend routes

**Prompt:**

> Problem number seven. Backend routes. So the React front end dashboard needs a backend it can call. And backend forward slash main dot py use fast API and add routes that do the following: Return the three tickets. And whether each one is open or resolved. So the ticket status. Then take a ticket ID, and run the agent team on that ticket. Then return recent agent events. So what each agent did and what they said and the tools that they used. So that the board can refresh. Then approve a payment or purchase once a human clicks approve. So the agent's only prepared to pay. This route is what actually changes cash. Then return the current checking balance from cash underscore accounts. Lastly, reset the database to the original values when we want to try a fresh run. Then from the back end forward slash folder, start the server with:
> uvicorn main:app --reload --port 8000 it should turn on the back end "http://localhost:9000, backend routes. So the React frontend dashboard needs a backend that you can call. In backend forward slash main dot py, use fast API and add routes that do the following. Return the three tickets and whether each one is open or resolved. So the ticket status. Then take a ticket ID and run the agent team on that ticket. Then return recent agent events. So what each agent did and what they said and the tools that they used so that the board can refresh. Then approve a payment or purchase. Once a human clicks approve, so the agents only prepare the pay, this route is what actually changes cash. Then return the current checking balance from cash underscore accounts. Lastly, reset the database to the original values when we want to try a fresh run. Then from the back end forward slash folder, start the server with it should turn on the back end at So the front end dashboard can call those routes. In output forward slash harness dot nd, list each route in one line. So what URL and what it does. That's all for problem seven.

**Follow-up prompt:** None needed.

---

## Problem 8: Agent dashboard

**Prompt:**

> Okay, problem eight. This is the agent dashboard. Build the front end dashboard in front end forward slash with React plus P plus TypeScript. The page should call the route that we built in problem seven. So right before this. At a minimum, the board should list all three tickets Let us pick one ticket and start the agent team on it. Show each agent what they're saying and like their conversations and what they're doing while the ticket runs. It should mark a ticket resolved. When the run finishes, assuming that the ticket has been resolved and satisfied, then show a short summary of what every agent did on that ticket. If they didn't do anything, just say they didn't do anything. Then let a human approve a pay or purchase when asked. Lastly, it should show the checking balance. And it should drop after approved pay. This dashboard should be very aesthetically pleasing. Easy to understand. And intuitive. Make it look good and sleek. This is a real desk people would want to sit at. So put thought into how it looks. Then tell the front end to talk to the back end at http://localhost:8000 . On the back end, allow the Vite page origin which is usually http://localhost:5173 so the browser can call those routes that like the browser is allowed to call the routes start the board with: npm run dev They should open the React desk in the browser so we, I can pick tickets or we can pick tickets and watch the agents work. Write output forward slash design dot md with what we're choosing for the dashboard look. So the layout, how agents read differently, how resolved tickets and cash show up, and why. So including the creative choices that make it feel special and something humans would actually enjoy using. It's kind of what we talked about earlier. That's problem eight. Go ahead and get it done.

**Follow-up prompt:** None needed.

---

## Problem 9: Resolve the tickets

**Prompt:**

> Okay, before testing the agents on a full run over the three tickets, one oh one, one oh two, one oh three, I want you to reset the working database which is data forward slash campus underscore customs underscore new dot db so that you start clean. Note the starting checking balance. Then run all three tickets. until you resolve each one. Open output forward slash desk underscore tickets.html from problem six. Then on each ticket tab, fill the actual section from this run. So when you're filling it, it should include which agents actually worked, what they delegated, the tools that they used, and then keep the expected section so we can compare the two. On the cache tab of the same output forward slash desk underscore tickets.html itemize the money. Itemize it based on the starting checking balance after the reset. And then for each ticket, so how much or how cash changed when that ticket resolved and why. So which pay and purchase and the dollar amount. And then the ending checking balance. Which must match the cash underscore accounts. In the working database. Wrong cash math. Is a terrible sin. So make sure. That it's all correct. And also save output forward slash resolved underscore tickets.json for each ticket so the ID final status short outcome what each agent contributed and any human approvals and then output forward slash resolved underscore board dot html and it's a page that we can double click with a screenshot of the React board for each resolved ticket so 101 102 and 103 And then append real runs to output forward slash audit underscore trail dot JSON. Finish output forward slash harness dot MD so it covers tables, MCP tools, all of the agents, all the API routes, the dashboard, and safety rules.

**Follow-up prompt:** see below.

**Follow-up prompt:**

> Uh, yeah, change the name to AI Foundation Student. HR. Why can't we finish ticket 103? Keep running it until it's resolved. That's what the directions for problem nine say. So I want you to include the actual section that we had to try it multiple times. Then send me a link to the board that I can double click and open and check it out.

**What was lacking after the first prompt:** After the first prompt, ticket 103 was still in progress after two runs and the payments were approved under my real name, so the follow-up changed the approver name, asked to keep running 103 until it resolved, and asked for the Actual section to show the multiple attempts.

**Second follow-up prompt** (after asking Claude what it thought, given the directions in earlier problems):

> Okay let's change done - resolved means the team made it's decision

**What was lacking after the first follow-up:** Five runs still left 103 in progress because the Boss's rules treated "waiting on cash or the customer" as unfinished, so this follow-up redefined resolved as "the team made its decision" (it resolved on the sixth run).

---

## Problem 10: Reflection

**Prompt:**

> Okay, for problem 10, open output forward slash desk underscore ticket study HTML and fill the reflection tab. How would you evaluate the performance of the agents on each ticket and why? For each ticket, how did actual compare to the expected plan you wrote earlier? What would have been simpler as one agent with tools and why? Describe three new problems Campus Customs might face that this agent team could solve with the tools you built. And describe three new problems Campus Customs might face that this agent team could not solve with the tools you built. And explain the tools and agents you would need to solve them.

**Follow-up prompt:**

> Tie every answer to this specific app and the three tickets that you ran. Use the ticket tabs and the cache tab on the same page as the evidence. Generic AI essays without campus customs details will score very, very low.

**What was lacking after the first prompt:** The first prompt listed the questions but didn't require every answer to point back to Campus Customs evidence, so the follow-up asked to tie each answer to the three tickets using the ticket tabs and Cash tab on the same page.

---

## Problem 11: Submit to GitHub

**Prompt:**

> All right, problem 11. We're going to push our code to a public GitHub repository. So that graders can clone it. And then submit the repo URL to Canvas. Which I'll take care of. But also put the repo URL in output forward slash GitHub underscore URL dot text. I don't want you to push the real dot env to the GitHub repo. But I do want you to include both database files under data forward slash which is the original in the working copy so graders can run this app easily. the README should explain copy original DB to the working copy when You need a clean run. Start the MCP server. Start fast API backend. Start the React board. Reset the DB before a full three ticket run.

**Follow-up prompt:** None needed.
