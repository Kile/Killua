import discord
from discord.ext import commands
import aiohttp
from matplotlib.pyplot import figure, plot, savefig, title
from numexpr import evaluate
from numpy import linspace
from io import BytesIO
from functions import custom_cooldown, blcheck


API_ADDR = 'http://api.mathjs.org/v4/'

class test(commands.Cog):

    def __init__(self, client):
        self.client = client
       


    @commands.command()
    @custom_cooldown(6)
    async def calc(self, ctx, *,args):
        if blcheck(ctx.author.id) is True:
            return
        #h Calculates any equasion you give it. For how to tell it to use a square root or more complicated functions clock [here](https://mathjs.org/docs/reference/functions.html)
    
        if not args:
            return await ctx.send(
                "Please give me something to evaluate.\n"
            
        )
        exprs = str(args).split('\n')
        request = {"expr": exprs,
               "precision": 14}
        async with aiohttp.ClientSession() as session:
            async with session.post(API_ADDR, data=json.dumps(request)) as resp:
                answer = await resp.json()
        if "error" not in answer or "result" not in answer:
            return await ctx.send(
                
                "An unknown error occurred during calculation!"
            )
        if answer["error"]:
            await ctx.reply("The following error occured while calculating:\n`{}`".format(answer["error"]))
            return
        await ctx.send("Result{}:\n```\n{}\n```".format("s" if len(exprs) > 1 else "", "\n".join(answer["result"])))

    @command()
    async def function(self, ctx, *, function):
        if blcheck(ctx.author.id) is True:
            return
	#t 1-2days (wtf)
	#r ID: 606162661184372736
	#c Could break Killua atm so restricted
    #h This plots a graph after my wish but since you can break Killua with it it is restricted to me until I find a solution
	    if ctx.author.id != 606162661184372736:
            return await ctx.send('Restricted command')
		try:
			x = linspace(-5,5,100)
			y = evaluate(function)

			# setting the axes at the centre
			fig = figure()
			ax = fig.add_subplot(1, 1, 1)
			ax.spines['left'].set_position('center')
			ax.spines['bottom'].set_position('center')
			ax.spines['right'].set_color('none')
			ax.spines['top'].set_color('none')
			ax.xaxis.set_ticks_position('bottom')
			ax.yaxis.set_ticks_position('left')

			# plot the function
			plot(x,y, 'g')
			title(str(function))
			buf = BytesIO()
			savefig(buf, format='png')
			buf.seek(0)

			graph = File(buf, filename= 'graph.png')



			await ctx.send(file=graph)
		except Exception as e:
			await ctx.send(e)


Cog = test

def setup(client):
    client.add_cog(test(client))

