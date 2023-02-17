## What is there to improve about a game like rock paper scissors?
Rock paper scissors was one of the first commands for Kllua and by far the most complex one for a long time as it was far above my skill level when I started. Though this mainly related to the asyncio things going on. 
However even with my limited knowledge something bothered me... the way the winner would be determined.

## The original way
This is what I did at the start to determine who won: 
```py
async def rpsf(choice1, choice2):

    if choice1.lower() == 'rock' and choice2.lower() == 'scissors':
        return 1
    if choice1.lower() == 'rock' and choice2.lower() == 'rock':
        return 2
    if choice1.lower() == 'rock' and choice2.lower() == 'paper':
        return 3
    if choice1.lower() == 'paper' and choice2.lower() == 'rock':
        return 1
    if choice1.lower() == 'paper' and choice2.lower() == 'paper':
        return 2
    if choice1.lower() == 'paper' and choice2.lower() == 'scissors':
        return 3
    if choice1.lower() == 'scissors' and choice2.lower() == 'paper':
        return 1
    if choice1.lower() == 'scissors' and choice2.lower() == 'scissors':
        return 2
    if choice1.lower() == 'scissors' and choice2.lower() == 'rock':
        return 3
```
## Better yet not great
Admitably this was horrible. So once I had gained some more experience I decided to rewrite it. This is what I came up with:
```py
async def rpsf(choice1, choice2):
    if choice1.lower() == choice2.lower():
        return 2
    if choice1.lower() == 'rock' and choice2.lower() == 'scissors':
        return 1
    if choice1.lower() == 'paper' and choice2.lower() == 'rock':
        return 1
    if choice1.lower() == 'scissors' and choice2.lower() == 'paper':
        return 1

    return 3
```
Now this is as simple and small as you can get the code for this and most people would stop there. However I have never liked the idea of static if checks. I wanted something dynamic, smart and cool. So I turned to many people's nightmare: maths.

## The math way
At the time I had the luck of having a very smart maths teacher who had studied maths at Oxford. After failing to come up for a foruma I eventually decided to ask him for help. 
My query was the following:
> The problem is as follows: Assuming I assign each option in rock paper scissors a number, I am trying to find a formula which can determine if, when given two of those numbers, number 1 wins or not. 

It took him less than a day to get back to. He suggested the following:
```js
let rock = -1
let paper = 0
let scissors = 1
```
The outputs would be :

`-1` Player 1 wins

`0` Draw

`1` Player 2 wins

And finally, the formula:
$$
f(p, q) = sin(pi/12*(q - p)*((q - p)^2 + 5)))
$$
p would be the numerical represntation of Player 1's choice, and q would be the numerical representation of Player 2's choice.

Let's take an example:
Player 1 chooses rock, so p = -1. Player 2 chooses paper, so q = 0.
$$
f(-1, 0) = sin(pi/12*(0 - (-1))*((0 - (-1))^2 + 5))) = sin(pi/12*(1)*(1 + 5)) = sin(pi/12*6) = sin(pi/2) = 1
$$ 
So the function returns 1, which means that Player 2 wins which is... correct.

#### Implementing it
```py
import math

def result(p: int, q: int) -> int:
    return int(math.sin(math.pi/12*(q-p)*((q-p)**2+5)))
```
That's it. One line. It's not the most readable code, but it's very efficient and it's very smart.

I have geniunely no idea how exactly this maths works but I do know that this proves that maths is not only cool but also magic.