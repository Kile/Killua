# Explanation of how testing works with Killua

Index
-

[How it is designed in code](#design)
[How tests are written](#how-tests-are-written)

## Design
__UML Diagram__
![Image](https://imgur.com/a/KVNIBTE)

In Essence one big class, `Testing` is subclassed first for each Cog, then that subclass for the cog is subclassed for each command.

This way, commands can be dynamically found from methods defined in the base class and `__subclassess__()`. After many months of playing around with this this seems like the cleanest and most effective layout to me.

__Logging__
The system also uses the `logging` module instead of printing results. This leads to the output level being configurable with the command line argument for testing (`python3 -m killua -t <logging-level>`) defaulting to `INFO`.

__Assertion checks__
All checks are written using the `assert` keyword. This way it is easier to identify where exactly a check has failed and what the actual result is. This is *insanely* useful from my testing. For example, a failed test output will look like this:
![Image](https://imgur.com/a/kfCNbGs)
Thanks to writing it like `assert actual == "Expected", actual` when catching the error `str(error)` will output the value of `actual` removing the necessity of having to debug it further (or if you are like me slapping print statements everywhere)

## How tests are written
As explained in the [design](#design) section, an actual test is within a subclass of a subclass of `Testing`. So to test a command `hello` of Cog `Group` this layout would be used:

```py
from ...cogs.group  import  Group # Importing the original cog

from ..types  import * # Importing all mock classes
from ..testing  import  Testing, test # Import base class and decorator

class  TestingGroup(Testing):
	def  __init__(self):
		super().__init__(cog=Group)

class Hello(TestingGroup):
	def __init__(self):
		super().__init__()
		self.command = self.cog.hello # This is not required, handy for more dynamic subclasses
```

__Writing a test__
Now that everything is layed out, you just need to write tests. These are methods on the command class they are tests for decorated with `@test` (as imported previously). These tests call the command function directly with a mock context accessible though `self.base_context` and any other necessary commands. 

After that, the context object will contain whatever was sent back by the command. So you can then check wether this is what you expected or not with pythons `assert` statement like this:

```py
# This is inside the Hello class
@test
async def should_work(self):
	await self.command(self.base_context)

	assert self.base_context.result.message.content == "hello", self.base_context.result.message.content
	# It is important to place whatever variable to test again after the comma so if it fails, 
	# the actual value of that variable can be displayed in the logs 
```