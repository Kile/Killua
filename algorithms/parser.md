A challange presented itself when I wanted to implement the mechanic for actually *using* spell cards.

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

    def _use_check(self, ctx: commands.Context, card: str, args: Optional[Union[discord.Member, int, str]], add_args: Optional[int]) -> None:
        """Makes sure the inputs are valid if they exist"""
        try:
            card: Card = Card(card)
        except CardNotFound:
            raise CheckFailure("Invalid card id")

        if not card.id in [x[0] for x in User(ctx.author.id).fs_cards] and not card.id in [1036]:
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

    async def _use_core(self, ctx: commands.Context, item: int, *args) -> None:
        """This passes the execution to the right class """
        card_class = [c for c in Card.__subclasses__() if c.__name__ == f"Card{item}"][0]
        
        l = []
        for p, (k, v) in enumerate([x for x in card_class.exec.__annotations__.items() if not str(x[0]) == "return"]):
            if len(args) > p and isinstance(args[p], v):
                l.append({k: args[p]})
            else:
                l.append(None)

        if None in l:
            return await ctx.send(f"Invalid arguments provided! Usage: `{self.client.command_prefix(self.client, ctx.message)[2]}use {item} " + " ".join([f"[{k}: {v.__name__}]" for k, v in card_class.exec.__annotations__.items() if not str(k) == "return"]) + "`", allowed_mentions=discord.AllowedMentions.none())
        kwargs = {k: v for d in l for k, v in d.items()}
        try:
            await card_class(ctx, name_or_id=item).exec(**kwargs)
        except Exception as e:
            await ctx.send(e.message, allowed_mentions=discord.AllowedMentions.none())

    @commands.hybrid_command(extras={"category":Category.CARDS, "id": 21}, usage="use <card_id> <required_arguments>")
    async def use(self, ctx: commands.Context, item: str, target: str = None, args: int = None):
        """Use spell cards you own with this command! Check with cardinfo what arguments are required."""
        
        if item.lower() == "booklet":

            def make_embed(page, embed, pages):
                embed.title = "Introduction booklet"
                embed.description = pages[page-1]
                embed.set_image(url="https://cdn.discordapp.com/attachments/759863805567565925/834794115148546058/image0.jpg")
                return embed

            return await Paginator(ctx, BOOK_PAGES, func=make_embed).start()

        try:
            self._use_check(ctx, item, target, args)
        except CheckFailure as e:
            return await ctx.send(e.message)

        args = await self._use_converter(ctx, args)
        args = [x for x in [target, args] if x]

        await self._use_core(ctx, item, *args)
```
This would
1) Check all arguments were provided correctly
2) Handle all check failures inside of the code of the card

Here is an example of how a card class would be structured:
```py
# Base class
class Card:
    def __init__(self, name_or_id: str):
        ...

    def _is_maxed_check(self, card: int) -> None:
        c = Card(card)
        if len(c.owners) >= c.limit * ALLOWED_AMOUNT_MULTIPLE:
            raise CheckFailure(f"The maximum amount of existing cards with id {card} is reached!")
            
 # Subclass
 class Card1010(Card):

    def __init__(self, name_or_id: str, ctx: commands.Context, **kwargs) -> None:
        self.ctx = ctx
        base = super().__new__(self, name_or_id=name_or_id, **kwargs)
        # Add all properties of base.__dict__ to self.__dict__
        self.__dict__.update(base.__dict__)
        
    def __new__(cls, *args, **kwargs) -> None:
        return object.__new__(cls)

    async def exec(self, card_id:int) -> None:
        user = User(self.ctx.author.id)

        if not user.has_any_card(card_id, False):
            raise CheckFailure("Seems like you don't own this card You already need to own a (non-fake) copy of the card you want to duplicate")

        self._is_maxed_check(card_id)
        user.remove_card(self.id)
        user.add_card(card_id, clone=True)

        await self.ctx.send(f"Successfully added another copy of {card_id} to your book!") 
 ```
 This allowed for everything to be more dynamic and after a while of testing work flawlessly together. It was a lot of work but it definitely payed off.
