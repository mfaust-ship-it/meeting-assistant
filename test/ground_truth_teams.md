# Ground Truth — Teams Transcript

**Source:** Official Microsoft Teams transcription
**Speakers:** Linus Armakola (LA), Marius Faust (MF), Sarosh Manzoor, Srihari Kookal (SK)

---

**[0:03] Linus Armakola:** Something.

**[0:04] Marius Faust:** It's more English with German accent.

**[0:09] Linus Armakola:** We do have a Pakistani and Indian accent in there as well.

**[0:12] Marius Faust:** Yeah, but I think if they work for long enough here, they will probably, yes.

**[0:18] Linus Armakola:** Get the German accent as well. OK, maybe restart the recording without the racist ****.

**[0:28] Sarosh Manzoor:** It used to be inclusive, I felt.

**[0:31] Marius Faust:** Uh.

**[0:34] Linus Armakola:** So who wants to start?

**[0:36] Marius Faust:** Yeah.

**[0:38] Linus Armakola:** OK, I can start.

**[0:39] Marius Faust:** Uh, what's? What's the agenda? Where's the agenda?

**[0:42] Linus Armakola:** Yeah, just, just, I thought that we just talk about what we've done and what we saw and how do we feel about it. And then at the end we can talk about what should we do next maybe.

**[0:47] Marius Faust:** Mhm.

**[0:56] Linus Armakola:** Um, yeah. So I implemented a signal that takes the customers.

**[0:57] Marius Faust:** Nice.

**[1:04] Linus Armakola:** Data that attributes that he provides from the tags and checks if he we can find these in the offers.

**[1:14] Linus Armakola:** It's pretty simple, straightforward. Also, Marius just updated it to be even better. So maybe now it's like a tokenized include check rather than what was it? Jacquard distance of the tokens basically.

**[1:32] Linus Armakola:** Which we discussed this morning.

**[1:33] Marius Faust:** Mm.

**[1:34] Marius Faust:** Almost.

**[1:36] Linus Armakola:** Almost.

**[1:37] Marius Faust:** Yes, so the jacka thing was the enhanced name similarity.

**[1:42] Linus Armakola:** Oh, OK, I thought we reused that there.

**[1:43] Marius Faust:** And you?

**[1:45] Marius Faust:** I was asking you that and you said probably and when I checked it was a basic was just a contains, so pretty similar to the tokenized unidirectional includes, but not quite.

**[1:49] Linus Armakola:** Yeah, I I wouldn't know. Claude did it, yeah.

**[1:57] Linus Armakola:** OK. Yeah.

**[2:06] Linus Armakola:** Yeah, OK, so uh, I did check data on the not improved version of that. It did show some results, especially for.

**[2:15] Linus Armakola:** Some. I don't recall which contracts I ran, but for some contract the like just using the brand actually already showed a lot of outliers, a lot of mismatches.

**[2:30] Linus Armakola:** Yeah, so I wanted to continue working on it today, but then Marius and I had a awesome discussion about everything this morning, including like to change to the tokenized include something.

**[2:47] Linus Armakola:** Instead of just contains, apparently. Um, and we also talked about.

**[2:54] Linus Armakola:** How we can proceed with all kinds of things, but I think I'll just leave that out here because it goes too far.

**[3:01] Linus Armakola:** I am now summarizing these ideas and I hope to.

**[3:08] Linus Armakola:** Discuss it with Marius before then showing it to everybody.

**[3:13] Linus Armakola:** Um.

**[3:15] Linus Armakola:** Yeah, but because of that I didn't add a work on a second signal. Maybe the nice thing about the signals that I added is that it's basically a signal factory where you can enter like all kinds of.

**[3:32] Linus Armakola:** Attributes and then it will produce a.

**[3:36] Linus Armakola:** Yeah.

**[3:38] Linus Armakola:** Uh, a signal for that attribute.

**[3:42] Linus Armakola:** Yeah, but it needs a mapping of customers attribute to a internal representation because then yeah, in order to be stable basically because in the end if we want to show this on the dashboard as well and if we just use the customers tag names for these then it would get very.

**[4:02] Linus Armakola:** Blurry and also in the future we might be able to improve this even further by having like hard coded fields like brand being extracted on Google, which apparently we don't right now to my understanding. So yeah.

**[4:19] Linus Armakola:** That's it. Long monologue questions.

**[4:24] Linus Armakola:** OK, maybe we do a quick quiz. Who listened?

**[4:28] Linus Armakola:** Marius listened. That's nice.

**[4:31] Sarosh Manzoor:** And listen to and listen, I swear.

**[4:35] Sarosh Manzoor:** No, because we talked about this I guess also yesterday quite a lot. So there's there are no obvious questions at the moment and this is a work in progress, so I'm sure there will be.

**[4:43] Linus Armakola:** No, maybe the last point that I made is like I should make it maybe a little bit louder. We do not extract the specifications of a product yet.

**[4:59] Linus Armakola:** And doing that could improve at least my signal drastically, my signals drastically. And I think also for other signals it could be cool to extract like the specifications that Google gives.

**[5:16] Srihari Kookal:** Extract this from where? Sorry.

**[5:18] Linus Armakola:** Let me maybe I just show an example too.

**[5:26] Linus Armakola:** So, um.

**[5:33] Linus Armakola:** There is this stuff.

**[5:34] Srihari Kookal:** Yeah.

**[5:36] Linus Armakola:** Which, for example, often contains stuff like the brand.

**[5:42] Srihari Kookal:** Yeah.

**[5:43] Linus Armakola:** Yeah, and this is kind of structured data.

**[5:49] Linus Armakola:** So.

**[5:51] Linus Armakola:** Comparing against this could be improvement for many, many signals.

**[5:57] Sarosh Manzoor:** Do we know if this is part of the JSPB or is this is a a separate request?

**[6:00] Linus Armakola:** No, I think this is a separate request.

**[6:01] Marius Faust:** This is not part of the JSPB.

**[6:02] Sarosh Manzoor:** OK.

**[6:06] Srihari Kookal:** So you're saying in in the signal you would make this request and then fetch this?

**[6:11] Linus Armakola:** Well, we were also talking about persisting data of products in the database. So we could enrich the database with this information. We could do it synchronously, as synchronously. I don't know. I don't wanna jump to any conclusions here, but it could be something that improves.

**[6:12] Srihari Kookal:** Oh.

**[6:16] Srihari Kookal:** Mm.

**[6:23] Srihari Kookal:** No.

**[6:29] Linus Armakola:** Accuracy a lot 'cause right now I am then only comparing against the product name.

**[6:31] Srihari Kookal:** No.

**[6:35] Srihari Kookal:** Yeah.

**[6:37] Linus Armakola:** Which is OK for some customers, but you know, could be better.

**[6:42] Linus Armakola:** Also, for example, if there is a manufacturer product name in here which isn't in this case, manufacturer product name can also be like a very strong indicator to also match the correct variant and everything.

**[6:57] Linus Armakola:** Yeah, maybe one thing. The signal I actually wanted to work on today is a specialized quantity checker. So I already have a quantity checker implemented now, which basically.

**[7:12] Linus Armakola:** Takes the customer's quantity tag and looks for that on the product, but I wanted to improve that to be something that understands quantity much better. Yeah, but I didn't get to that. I still think this is a valuable thing to do in the future.

**[7:32] Linus Armakola:** So, Srihari, tell us about your secret GTIN project.

**[7:36] Srihari Kookal:** Uh.

**[7:42] Srihari Kookal:** This is definitely not my original idea. This is what Andreas tried last weekend where he was simply scraping all the URLs of the offers itself and then seeing if that page showed GTIN or not. I converted this to a signal, ran it on.

**[8:01] Srihari Kookal:** 100K products, so actually queued it to run for one point, you know, almost 200K products, but then.

**[8:11] Srihari Kookal:** Sorry 300K products is what I ran the signal for. 200K did not run because I just had the very basic HTTP setup and 200K error out saying the connection pool had too many connections.

**[8:28] Srihari Kookal:** Of the 100K requests I made, I didn't get. I did not get a GTIN for 94% of the requests. I got the GTIN for a small set of them.

**[8:44] Srihari Kookal:** And of that a very small was set for I. So I got 400 GTIN confirmed and then 26 GTIN mismatched. So I don't know 5% or so they're mismatches.

**[9:01] Srihari Kookal:** Um.

**[9:05] Srihari Kookal:** I think that connectivity can be improved. So this is the signal I would keep because for me the confidence of the signal is really high. So if you look for a GTIN in an offer page and then you in a.

**[9:23] Srihari Kookal:** Well, we have. I have to learn the terms. I don't know if it's called a product display page, but wherever the retailer shows the product, if it shows the exact GTIN that we searched for, then it's 100% match. If it is mismatching, then it's a mismatch.

**[9:39] Srihari Kookal:** And yesterday I had a very important session with Ehsan where we first talked about this signal, but then there was a second ticket that I picked up, which was Ehsan's idea for building a regression model for matching.

**[9:56] Srihari Kookal:** So what what we intended to do was that since the GTIN signal is very strong, if we see a GTIN match then it's definitely a match. We would use that as a training data. So matches and mismatches from the GTIN signal would be used as a training data.

**[10:14] Srihari Kookal:** To train logarithmic regression classifier and that would in turn become a signal. So we would train the weights, use the weights in a signal and that would become a.

**[10:30] Srihari Kookal:** Signal with with its own unknown heuristics, but basically whatever it learns from this and in the end what Ehsan proposed is that we have a classifying pipeline where we have a set of rules in the very beginning which do all the determinants.

**[10:50] Srihari Kookal:** Probabilistic signals that we have now, like say data mismatches, name mismatches, all the for sure yes and no signals get right first and then afterwards we send it to some probabilistic system like this which says OK, this likely looks correct or wrong.

**[11:09] Srihari Kookal:** So that was all learning for me. What I would take away from this is I will try to productionize the GTIN signal itself so that we have a better way of making requests and.

**[11:24] Srihari Kookal:** Providing that that extra confidence that OK, this is a GTIN match, so it probably definitely is a match. That's one thing. Second thing throughout the thing I learned is that our immediate problem is that we have a lot of bad search attempts.

**[11:43] Srihari Kookal:** So even though the the whole tribunal tries to achieve even further and broader goals for us, I think the immediate problem is that we have a lot of bad Google search attempts. So whatever we get while we work on this, we should just keep clearing it.

**[12:03] Srihari Kookal:** As we go, I think we.

**[12:08] Srihari Kookal:** We talked about this before. I was not so convinced about it. Then I was also saying why do we want to do actions now? Let's do let's build actions later. But that's changed for me. Now I'm like, OK, these are obvious mismatches. We should just clear them off and then.

**[12:25] Srihari Kookal:** Get rid of them. Yeah, that's a bit of light.

**[12:31] Srihari Kookal:** That's me.
