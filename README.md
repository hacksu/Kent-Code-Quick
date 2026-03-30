# Kent Code Quick
This is basically a writeup of everything the event should be.

## Motivation (by Andrew Roddy)
This section is kind of to get you in my headspace to understand why I want to do this event. If you are a developer you can probably skip this. 
This event essentially hinges on three ideas I have been thinking about for a while. These all focus on people learning as much as possible at this event.

### No AI
The first one is no AI. Currently I see AI as a poison steroid. It makes the weak extremely strong and the strong even stronger. The problem is the more you use it the worse you get at programming. I said that too confidently. It feels like for me, that the more I use it the worse I get at programming. Not just like a plataeu but literally worse. I understand that everyone wants to 'leverage AI' but it feels like the more I do the less leverage I have myself as a programmer. This is to say, in this event we will try our best to make AI as inconvenient to use as possible to force people to learn as they build.

### Copy then expand
Whether it is music production, photo editing, video editing, or programming, I have always learned the most from trying to copy what others have done. Trying to recreate software, a song, an image, or a video effect forces you to get into the headspace of the author and understand why they chose to do what they did. This forces you to learn techniques you didn't know before and expand what you think is possible in the medium. This allows you to learn to do things you would have never learned as you didn't know they were an option. Once you have enough of these tools, you can then use them to express yourself in new ways and eventually add your own flair and style to these techniques. This is to say, participants will be recreating an already existing project, from scratch, then adding their own flair and style to it. They will be judged on how well they recreated the project and how much cool stuff they added.

### Constraints
Constraints create creativity, or something like that. Usually when I am under real time pressure is when I learn the most. While making the HacKSU reels there was demand for me to complete them in a reasonable amount of time. This forced me to cut things that were not important to include and allowed me to focus on the most important elements of the process. Another constraint is the idea itself. Although I came up with a lot of the ideas for the HacKSU reels I didn't come up with all of them. Because of this, I had to actually learn how to implement someone else's idea to the best of my ability. Another constrainit is project scope. Having the scope be small make it easy to pivot when something does not work. This allows people to learn in a less stressful environment. At a 24 hour hackathon you are spending 24 hours of your time on a project. Similar to games like League of Legends the reason you care about the match isn't only because you want to win, its because of the large amount of time you sank into it. These three constraints are why participants will have 45 minutes to complete the project.

## The Event Plan
So people will show up to this event with their own laptops. They will then go to the website, enter a room code, and wait in that room. After this I will then explain the event better and show what they are coding. The event will begin. When the event begins they will see an IDE (like vscode) in their window. They can code and will have a live HTML/CSS preview on the right. We can think about having framework specific challenges later but these seem to be the easiest rn. Also having JavaScript would be cool but those are enough for now. 
If a user leaves the website they will be penalized by time. They will not be able to copy or paste in their code.
Because we won't be allowing them to leave the website we should still allow external sources though. We could either just like copy then entire docs into a window in their web IDE or have a browser built in that only shows whitelisted sites (Stack Overflow/W3 Schools)
Then, on the projector, it will show a live preview of everyone's projects as they code them. This sounds extrememly difficult and is kind of a moonshot but would be really cool. Also a large count down timer will be on the screen. It would also be nice to have everyone's name on the project they are currently working on. I think the live preview would basically be us just constantly saving and re running their website. Lastly, when the timer hits zero it should start going into the negatives, this is incase something happens that delays us. I will manually put an end to the event and when that happens we will go through each one one by one showing them on the screen. The organizers would then select a winner like while in a different room and yay we are done!

## The Software Idea
- website that contains an IDE.
    - IDE needs to have the ability to pull up documentation that we specifically allow.
    - able to live preview the HTML/CSS that the users are typing.
    - penalize when tabbing out. I am thinking 5 seconds the first time, 25 the next time, 1m, 2m, 4m, 8m, 16m etc etc.
    - no copy and paste, 

- presenter preview
    - large timer with everyone's project live preview displayed
    - on each project the persons name
    - large timer in the top center
    - ability for admin to end event at time

- ability to flip through everyone's project and project code (basically assume everyone's view as admin)
    - this should make it easy for everyone to see everyone else's project

- Landing page where people can type in the entry code that is displayed on screen