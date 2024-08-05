A challenge presented itself when I wanted to implement the mechanic for actually *using* spell cards.

I couldn't create 20 commands being named `/use1001`, `/use1002`... instead I had to come up with something better.

At first I created something on the lines of 
```py
@commands.command
async def use(self, ctx, card: str, args1: Union[int, discord.Member, str] = None, args2: Union[int, str] = None):
    if card == "1001":
      await self.card_1001(args1, args2)
    elif card == "1002":
        await self.card_1002(args1, args2)
    elif ...
```
which, as it happens with about **30** spell cards became quite a long list and needed a lot of subroutines in the class.

After thinking about it for a while I had the following idea:

If I made all cards classes, I could have one set method being the one that does whatever the spell card is supposed to while subclassing a common card class which would contain shared subroutines.
As for how arguments would work and be validated? I took inspiration from the very library I was using, discord.py, where whatever you would annotate command parameters as would be taken as their type. So I decided that whatever I annotated for this special subroutine on each card class would be the arguments it needed. 

This would eventually enable the command to boil down to:
```py

    async def _use_check(
        self,
        ctx: commands.Context,
        card: str,
        args: Optional[Union[discord.Member, int, str]],
        add_args: Optional[int],
    ) -> Card:
        """Makes sure the inputs are valid if they exist"""
        try:
            card: Card = await Card.new(card)
        except CardNotFound:
            raise CheckFailure("Invalid card id")

        if not card.id in [
            x[0] for x in (await User.new(ctx.author.id)).fs_cards
        ] and not card.id in [1036]:
            raise CheckFailure("You are not in possesion of this card!")

        if card.type != "spell":
            raise CheckFailure("You can only use spell cards!")

        if card.id in [*DEF_SPELLS, *VIEW_DEF_SPELLS]:
            raise CheckFailure("You can only use this card in response to an attack!")

        if args:
            if isinstance(args, discord.Member):
                if args.id == ctx.author.id:
                    raise CheckFailure("You can't use spell cards on yourself")
                elif args.bot:
                    raise CheckFailure("You can't use spell cards on bots")

            if isinstance(args, int):
                if int(args) < 1:
                    raise CheckFailure("You can't use an integer less than 1")

        if add_args:
            if add_args < 1:
                raise CheckFailure("You can't use an integer less than 1")

        return card

    async def _use_core(self, ctx: commands.Context, card: Card, *args) -> None:
        """This passes the execution to the right class"""
        card_class: Type[IndividualCard] = next(
            (c for c in Card.__subclasses__() if c.__name__ == f"Card{card.id}")
        )

        l: List[Dict[str, Any]] = []
        for p, (k, v) in enumerate(
            [
                x
                for x in card_class.exec.__annotations__.items()
                if not str(x[0]) == "return"
            ]
        ):
            if len(args) > p and isinstance(args[p], v):
                l.append({k: args[p]})
            else:
                l.append(None)

        if None in l:
            return await ctx.send(
                f"Invalid arguments provided! Usage: `{(await self.client.command_prefix(self.client, ctx.message))[2]}use {card.id} "
                + " ".join(
                    [
                        f"[{k}: {v.__name__}]"
                        for k, v in card_class.exec.__annotations__.items()
                        if not str(k) == "return"
                    ]
                )
                + "`",
                allowed_mentions=discord.AllowedMentions.none(),
            )
        kwargs = {k: v for d in l for k, v in d.items()}
        try:
            await cast(
                IndividualCard, await card_class._new(name_or_id=str(card.id), ctx=ctx)
            ).exec(**kwargs)
            # It should be able to infert the type but for some reason it is not able to do so
        except CheckFailure as e:
            await ctx.send(e.message, allowed_mentions=discord.AllowedMentions.none())

    @check()
    @commands.hybrid_command(
        extras={"category": Category.CARDS, "id": 21},
        usage="use <card_id> <required_arguments>",
    )
    @discord.app_commands.describe(
        item="The card or item to use",
        target="The target of the spell",
        args="Additional required arguments by the card",
    )
    @discord.app_commands.autocomplete(item=use_cards_autocomplete)
    async def use(
        self, ctx: commands.Context, item: str, target: str = None, args: int = None
    ):
        """Use spell cards you own with this command! Check with cardinfo what arguments are required."""

        if item.lower() == "booklet":

            def make_embed(page, embed: discord.Embed, pages):
                embed.title = "Introduction booklet"
                embed.description = pages[page - 1]
                embed.set_image(
                    url="https://cdn.discordapp.com/attachments/759863805567565925/834794115148546058/image0.jpg"
                )
                return embed

            return await Paginator(ctx, BOOK_PAGES, func=make_embed).start()

        try:
            card = await self._use_check(ctx, item, target, args)
        except CheckFailure as e:
            return await ctx.send(e.message)

        args = [
            x
            for x in [
                await self._use_converter(ctx, target),
                await self._use_converter(ctx, args),
            ]
            if x
        ]

        await self._use_core(ctx, card, *args)
```
This would
1) Check all arguments were provided correctly
2) Handle all check failures inside of the code of the card

## THIS SYSTEM IS OUTDATED. I improved it but too lazy to update the classes below rn. 

As for the actual class, all individual class subclass two classes. 
### 1) Card
```py
# Base class
@dataclass
class Card:
    async def new(self, name_or_id: str) -> Card:
        ...

    async def _is_maxed_check(self, card: int) -> None:
        c = await Card.new(card)
        if len(c.owners) >= c.limit * ALLOWED_AMOUNT_MULTIPLE:
            raise CheckFailure(f"The maximum amount of existing cards with id {card} is reached!")
```
This class is the base class for all cards and contains all shared subroutines like checks for maxed cards (the example here). It also contains all information about the card like its name, id, type, etc.

### 2) IndividualCard
```py
# ABC abstract class IndividualCard
class IndividualCard(ABC):
    """A class purely for type purposes to require subclasses to implement the exect method"""
    ctx: commands.Context

    @classmethod
    async def _new(cls, name_or_id: str, ctx: commands.Context) -> Card:
        base = await Card.new(name_or_id=name_or_id)
        setattr(base, "ctx", ctx)
        setattr(base, "exec", partial(cls.exec, self=base))
        return base

    @abstractmethod
    async def exec(self, *args, **kwargs) -> None: ...
```
Before the async rewrite, this class was much cleaner and merely served the purpose of type hinting that individual card classes had to implement the `exec` method. However, after the async rewrite, `Card.new` always returned an instance of `Card`, not implementing the `exec` method. So I had to come up with a way to dynamically add the `exec` method to the instance of `Card` that was returned by `Card.new`. This was done by using a class method `_new` which would return an instance of `Card` with the `exec` method added to it. This was done by using the `partial` function from the `functools` module to bind the `exec` method of the subclass to the instance of `Card` that was returned by `Card.new`. 

This code is not clean, it doesn't follow the idea of an abstract class and I much preffered the old version. However, it was the only way I could find to make it work.

### The subclass
```py
# Subclass
class Card1010(Card, IndividualCard):

    async def exec(self, card_id: int) -> None:
        user = await User.new(self.ctx.author.id)

        if not user.has_any_card(card_id, False):
            raise CheckFailure(
                "Seems like you don't own this card You already need to own a (non-fake) copy of the card you want to duplicate"
            )

        await self._is_maxed_check(card_id)
        await user.remove_card(self.id)
        await user.add_card(card_id, clone=True)

        await self.ctx.send(
            f"Successfully added another copy of {card_id} to your book!"
        )
 ```
The main idea of this system is to make subclasses as easy to add and worry free as possible. Most checks are implemented in the `Card` class and just require one line of code in the subclass. The `exec` method is the only method that is required to be implemented in the subclass and it is the method that is called when the card is used. As a bonus, each subclass is added to `Card.__subclasses__()` so that the `_use_core` method can find the correct class to call the `exec` method on without it being hardcoded.
