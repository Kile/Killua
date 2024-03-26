*(this is the original description of the Pull Request introducing this algorithm)*

The main purpose of this branch was to rewrite the poll command but it also includes small other changes.


## Why rewrite
It started when I used Killua for a poll for my server. I noticed a very simple but big mistake I made. One of the options had 6 voted (5 shown as mentions, 1 being "+ 1 more...") but when I would click on said option nothing would happen. 

![](https://i.imgur.com/gQm0Z1i.png)

It turns out that something did in fact happen. However, the way Killua used to check for votes is check the mention. However as there was "+ 1 more..." ofc it would never register more than 5 votes, then add you as the sixth. This would repeat leading to no option ever being able to get more than 6 votes. It would also allow you to vote for two options if you were the "+ 1 more..." in one of them as there was no id associated with that "1 more".

## So use a database, problem solved.
Well... no. For two reasons.
1) I was quite proud polls being my first command in Killua with persistent views that do not need a database, persistent meaning they still work after a bot restart by reading the custom ids of a button
2) Killua is all about learning more about programming for me. Sure a database was the easy way out. But that would not have taught me anything.

Because of these reasons I thought about how I could implement this without using a database

## The journey
The task was to store as much as possible in one discord message, the poll message, as that was the only information I would be able to access on a new button click. There were two places where I could store information:
1) The embed. This would be visible to the user so there could not be too much information as it would look off. I could save things like what the options were and the first 5 users that voted on an option were.
2) The custom ids of the buttons. This would not be visible to users but had a 100 character limit for each button.

I quickly realised that for it to be able to scale I *would* need a database. But I decided to make this as well and use the database for unlimited votes as a premium feature.

My initial idea was in each button's custom id I could save the option and votes if there were more than 5. It would then look something like this: 
```py
poll:option-1:606162661184372736:495556188881027092,270148059269300224
```

Quickly I realised that 
1) the author id (after the option-1) would only be needed in the close button as it was necessary to store it 5 times.
2) option was unnecessary long and could be reduced to `opt`
3) Lastly and most importantly that discord ids were too damn long. Up to 19 characters per id. That means a maximum of 4 extra votes on an option. Not a huge bonus. 
So I needed to find a way to reduce the length of the ids while still being able to compare them to normal ids.

### The compression
My first approach was using encryption. Specifically XOR encryption. My idea was to split the id in two half, XOR both half, then take the new result and repeat it long enough until I had a small string. However it was not unlikely for those end results to overlap, producing false positives. So I had to chose an end length reliable enough while also being as short as possible.
In my tests I found out 4 characters had the best short to unique ratio, scoring an about 10% overlap in my tests while with its 4 characters would allow for much more votes.

![](https://i.imgur.com/8Io2AZ5.png)

But I wasn't satisfied. I tried to bring the number down through various other algorithms before so it would be more unique with a smaller amount of characters. This gave me an idea: number bases. 
As an example, the number "10" in binary (base 2) is `1010`. 4 characters. Yet in hexadecimal, it is `A` (base 16), one character! So if I was now able to convert a discord id in a very large base it would have a very small amount of characters!

After experimenting I quickly discarded the old XOR idea completely and focused on this. I found out that there were 11000 unicode characters so I chose base 100000 as the base I would use. I did not stick to normal base standards (eg start with A after 9) as as long as it remained consistent it did not matter. So now I was able to reduce a discord id to about 3-4 characters which were completely unique to that id! But I thought I could do better. It did not have to be 100% accurate. 
Because the last characters of a number are the most unique digits of that number as they are the most exact I started experimenting with the accuracy of only using the last 2 characters/digits. And that worked pretty well.

![](https://i.imgur.com/OI5ghpc.png)

![](https://i.imgur.com/X9Ge7pA.png)

So I decided this is what I would use as you would never have to go from compressed id back to id, just from id to compressed id the last two characters were enough for a check. After all `2^1000 * 2^1000` is still a pretty large number of possibilities. However I did decide I would keep the author id in full accuracy to make sure no one else would be able to close the poll, even if the probability was small.

## One more thought

Another thought I had that if there was to be a poll on a huge server all options would quickly be at the max amount and even though the members may favour one side, all options would have an even number of votes. So I decided I would allow for other votes to be saved somewhere in case there was not enough space for them but there was in another custom id.

I quickly gave up on doing this for all button and dedicated the custom id of the close button for this.

## The implementation

Overall this was not easy to implement, but I think I have managed to do so. Theoretically it is incredibly reliable, should not need a database unless on huge servers and looks good. I also decided to not use a database backup for war questions which use the same code as they cannot be closed and can easily fill up my db.
