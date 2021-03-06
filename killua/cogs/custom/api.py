from dataclasses import dataclass

@dataclass
class MessageSend:
	message: str
	channel_id: int
	reply_id: int

@dataclass
class MessageSendAcknowledge:
	id: int

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
