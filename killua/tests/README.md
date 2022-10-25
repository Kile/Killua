# Explanation of how testing works with Killua

Index

[The design of the testing system](#design)

[How tests are written](#how-tests-are-written)

[Troubleshooting](#troubleshooting)

## Design
### The mock classes

In general, testing a command works by controlling everything *but* the command callback itself. That means of all relevant discord objects there exists a class in `killua/tests/types`, mocking their methods and attributes that are used inside of the commands. Their `__class__` is set to the discord class they mock to avoid an `isinstance(argument, discordClass)` inside of a command falsely failing on a mock class.

There also exist mock classes for pymongo database stuff in a different file location as the tests are designed to be able to work completely offline (which is currently not fully archived) and the database should not be spammed when all tests are run. When tests are run, the `DB` class containing all details of connections will automatically switch to the mock data instead of the real one.

### How responses can be verified

All mock classes of messagables (`Member`, `TextChannel`, `Context`...) have an overwritten `send` method that, instead of actually sending it somewhere, creates a mock message of how a message object would *look like* if sent, then sets this as the attribute `result` of the supplied `Context` object to the command. 

This is why all messagables that *aren't* `Context` have a property referring back to it so they are able to set that attribute.

### How `View`s and `Bot.wait_for` is handled

Both `View` and `Bot.wait_for` normally require another user interaction for the command functioning normally. For `View` it also strongly depends on what the user does on what the commands response is. They are handled by:

+ `Bot.wait_for`
For this, `asyncio.wait` is used to call the command and a method of `Bot` that resolves the `wait_for` at the same time. 
```py
asyncio.wait({command(context), Bot.resolve("message", MockMessage())})
```

+ `View`s
Views were harder to tackle as they are much more complex in what could be responded to them. How it was solved is by before calling the command callback, the method `respond_to_view` of the mock `Context` supplied can be set which takes in one parameter `context`. Through `context.current_view` it can then access the view and go through it's `children` to modify values and call callbacks. 
`respond_to_view` overwrites `View.wait()` if a `View` is supplied to a `send` method and so it will be called if the view requires a response, also avoiding the trouble of the tests taking much longer if the view had to be responded to from a separate asyncio loop. In code, this would simply look like this:
```py
async  def  respond_to_view_no_settings_changed(context: Context):
	for  child  in  context.current_view.children:
		if  child.custom_id == "save":
			await  child.callback(MockInteraction(context))
			
context.respond_to_view = respond_to_view_no_settings_changed
await command(context)
```

### UML Diagram of Testing structure

![Image](https://imgur.com/9lmhQXp.png)

In Essence one big class, `Testing` is subclassed first for each Cog, then that subclass for the cog is subclassed for each command.

This way, commands can be dynamically found from methods defined in the base class and `__subclassess__()`. After many months of playing around with this this seems like the cleanest and most effective layout to me.

### Logging

The system also uses the `logging` module instead of printing results. This leads to the output level being configurable with the command line argument for testing (`python3 -m killua -t <logging-level>`) defaulting to `INFO`.

> **Warning**
> Due to a fix to an issue with assertion errors displaying even though they are matched, **all console output without `INFO:`, `DEBUG:`, `WARNING:`, `ERROR:` or `CRITICAL:` will not be printed to the console.** So for debugging either use `logging.debug` or `print("DEBUG:", thing)`

### Assertion checks

All checks are written using the `assert` keyword. This way it is easier to identify where exactly a check has failed and what the actual result is. This is *insanely* useful from my testing. For example, a failed test output will look like this:

![Image](https://imgur.com/CxYLfoS.png)
Thanks to writing it like `assert actual == "Expected", actual` when catching the error `str(error)` will output the value of `actual` removing the necessity of having to debug it further (or if you are like me slapping print statements everywhere)

## How tests are written

### The layout
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

### Writing a test

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
For writing tests including `Views`s or `Bot.wait_for` see [How `View`s and `Bot.wait_for` is handled](#how-views-and-bot.wait_for-is-handled)

## Troubleshooting

### `Views`
Commonly view responses cause a bit of trouble, though luckily not as much as they used to. When a view response isn't as intended, check the following:
+ Is `context.timeout_view` set to `True`? If it is, the view automatically instantly times out
+ Is the callback you designed the view for the last time the callback is used? 

### An issue with `User`

Make sure the `User` database entry is exactly how you want it to be before the command. Resetting the database can often cause more harm than good!