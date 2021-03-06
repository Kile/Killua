from dataclasses import dataclass
from discord import Message
from typing import Optional

@dataclass
class MessageData:
	id: int
	author_id: int
	webhook_id: Optional[int]

	ref_guild_id: Optional[int]
	ref_channel_id: Optional[int]
	ref_message_id: Optional[int]

	content: str
	edited: Optional[int]
	ty: int
	flags: int
	tts: bool
	pinned: bool

	mentions_everyone: bool

	@staticmethod
	def from_message(message: Message):
		return MessageData(
			message.id,
			message.author.id,
			message.webhook_id,
			None if message.reference is None else message.reference.guild_id,
			None if message.reference is None else message.reference.channel_id,
			None if message.reference is None else message.reference.message_id,
			message.content,
			None if message.edited_at is None else message.edited_at.timestamp(),
			0, # TODO: message.type to int
			message.flags.value,
			message.tts,
			message.pinned,
			message.mention_everyone
		)

@dataclass
class MessageTooLargeError:
	pass

@dataclass
class UnknownTextChannelIdError:
	pass

@dataclass
class UnknownMessageIdError:
	pass

@dataclass
class InsufficientPermissionsError:
	pass

@dataclass
class ServerError:
	pass

@dataclass
class MessagePageLoad:
	count: int
	channel_id: int
	before: Optional[int]
	after: Optional[int]

@dataclass
class MessagePageLoadAcknowledge:
	messages: list[MessageData]

@dataclass
class MessageSend:
	message: str
	channel_id: int
	reply_id: int

@dataclass
class MessageSendAcknowledge:
	message: MessageData
