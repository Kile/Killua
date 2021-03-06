#![feature(new_uninit)]

use std::{
	convert::TryFrom,
	mem::MaybeUninit,
	num::NonZeroU8
};

pub mod raw {
	#[repr(C)]
	pub struct ContextEnvironment {
		pub guild_id: u64,
		pub channel_id: u64,
		pub message_id: u64
	}

	#[repr(C, align(4))]
	#[derive(Clone, Copy, Debug)]
	pub struct Message {
		pub id: u64,
		pub author_id: u64,
		pub webhook_id: u64,
		pub reference_guild_id: u64,
		pub reference_channel_id: u64,
		pub reference_message_id: u64,
		pub edited: u64,
		/// This field contains the byte length, and part of the string length.
		///
		/// Where ones represent the byte length, and zeros represent the string
		/// length, the format of this field on a bit level is as follows.
		/// ```
		/// 1111111111111000
		/// ```
		pub content_length: u16,
		/// This field contains part of the string length.
		///
		/// These bits in this field come directly after the string length bits in
		/// [`content_length`].
		pub content_length_cont: u8,
		pub flags: u8,
		pub r#type: u8,
		/// This field contains the reactions length, whether or not this message is
		/// pinned, whether or not this message uses tts and whether or not this
		/// message pings everyone.
		///
		/// Where threes represent the reactions length, two represents the pinned
		/// bool, one represents the tts bool, and zero represent the everyone ping
		/// bool, the format of this field on a bit level is as follows.
		/// ```
		/// 33333210
		/// ```
		pub reactions_length_etc: u8,
		pub mentions_length: u8
	}

	#[repr(C)]
	pub struct Reaction {
		pub count: u32,
		/// This field represents whether or not this was reacted to by you and
		/// whether or not this reaction is a emoji or emote.
		///
		/// Where zeros represent nothing, one represents whether or not this was
		/// reacted to by you and two represents whether or not this reaction is an
		/// emote, the format of this field on a bit level is as follows.
		/// ```
		/// 00000012
		/// ```
		pub flags: u8,
		/// This field represents the UTF-8 string data of this emoji, or the id of
		/// this emote.
		///
		/// Whether or not this is emoji data or an emote id is determined by
		/// [`count`].
		pub id: u64
	}

	#[link(wasm_import_module = "discord_bridge")]
	extern "C" {
		/// Returns the Discord environment.
		///
		/// Parameters
		/// ----------
		/// #1: u64, ID of the guild.
		/// #2: u64, ID of the channel this interaction is in.
		/// #3: u64, ID of the message this interaction is triggered from.
		pub fn context_environment(env: *mut ContextEnvironment);

		/// Writes `msg_len` messages from `channel` into `msg_buf`.
		///
		/// Arguments
		/// ---------
		/// 1. `buf` - Mutable pointer to `Message`s, written if successful, must
		/// 	not be null
		/// 2. `buf_len` - Size of `buf` in number of `Message`s. The most
		/// 	significant bit is ignored, and is instead used for whether or not
		/// 	messages will be read after or before `from`.
		/// 3. `channel` - The channel the messages will be read from
		/// 4. `from` - The message to start reading from. The most significant of
		/// 	`buf_len` determines whether or not messages will be read before or
		/// 	after this.
		///
		/// Return Value
		/// ------------
		/// The returned value represents the success.
		/// - `0` to `isize::MAX` - Call was successful, represents number of
		/// 	messages written
		/// - `-1` - Unknown error
		pub fn message_load(buf: *mut Message, buf_len: usize, channel: u64,
			from: u64) -> isize;

		/// Writes data about a message to the supplied pointers.
		///
		/// Arguments
		/// ---------
		/// All sizes of buffers determined by data in `Message`. If a pointer is
		/// null, then it is not written to. If all pointers are null, this call
		/// does nothing. All pointers only written to if successful.
		/// 1. `id` - The id of the message that will be populated.
		/// 2. `content` - Mutable pointer to UTF-8 data, may be null
		/// 3. `reactions` - Mutable pointer to `Reaction`s, may be null
		/// 4. `mentions` - Mutable pointer to ids of mentions, may be null
		/// 5. `mention_role` - Mutable pointer to a pointer to ids of mentions. The
		/// 	pointed to pointer written to here represents the start of role
		/// 	mentions. All mentions before this pointer in `mentions` are user
		/// 	mentions. Must be non null if `mentions` is non null, must be null
		/// 	otherwise.
		///
		/// Return Value
		/// ------------
		/// The returned value represents the success.
		/// - `0` - Call was successful
		/// - `1` - Unknown error
		pub fn message_populate(id: u64, content: *mut u8, reactions: *mut Reaction,
			mentions: *mut u64, mention_role: *mut *const u64) -> u8;

		/// Sends a message `msg` of length `msg_len` in bytes.
		///
		/// Arguments
		/// ---------
		/// 1. `msg` - Immutable pointer to UTF-8 data, must not be null
		/// 2. `msg_len` - Size of `msg`'s data in bytes
		/// 3. `channel` - The channel the message will be sent to
		/// 4. `reply` - The message this message will be sent in response to, 0 for
		/// 	none.
		/// 5. `id` - Mutable pointer to the id of the message to be sent, written
		/// 	if successful.
		///
		/// Return Value
		/// ------------
		/// The returned value represents the success.
		/// - `0` - Call was successful
		/// - `1` - Message data was too long (over 2000 characters)
		/// - `2` - Specified `channel` doesn't exist
		/// - `3` - Specified `reply` doesn't exist
		/// - `4` - Insufficient permissions
		/// - `5` - Unknown error
		pub fn message_send(msg: *const u8, msg_len: usize, channel: u64,
			reply: u64, id: *mut u64) -> u8;
	}
}

pub fn context_environment() -> (u64, u64, u64) {
	unsafe {
		let mut context = MaybeUninit::uninit();
		raw::context_environment(context.as_mut_ptr());

		let raw::ContextEnvironment {guild_id, channel_id, message_id} =
			context.assume_init();
		(guild_id, channel_id, message_id)
	}
}

pub fn message_load(count: usize, channel: u64, from: u64)
		-> Result<Vec<raw::Message>, NonZeroU8> {
	unsafe {
		let mut messages = Box::new_uninit_slice(count);
		let written = raw::message_load(
			messages[0].as_mut_ptr(), count, channel, from);

		match usize::try_from(written) {
			Ok(written) => {
				let messages = Box::into_raw(messages) as *mut _;
				Ok(Vec::from_raw_parts(messages, written, count))
			},
			Err(_) => match u8::try_from(written.abs()) {
				Ok(error) => Err(NonZeroU8::new_unchecked(error)),
				Err(_) => panic!("error number out of bounds")
			}
		}
	}
}

pub fn message_populate(message: &raw::Message)
		-> Result<(String, Vec<raw::Reaction>, Vec<u64>, usize), NonZeroU8> {
	unsafe {
		let content_len = (message.content_length & 0b1111111111111000) as usize;
		let reactions_len = (message.reactions_length_etc & 0b11111000) as usize;
		let mentions_len = message.mentions_length as usize;

		let mut content = Box::new_uninit_slice(content_len);
		let mut reactions = Box::new_uninit_slice(reactions_len);
		let mut mentions = Box::new_uninit_slice(mentions_len);
		let mut split = MaybeUninit::uninit();
		let result = raw::message_populate(message.id, content[0].as_mut_ptr(),
			reactions[0].as_mut_ptr(), mentions[0].as_mut_ptr(), split.as_mut_ptr());

		match NonZeroU8::new(result) {
			None => {
				let content = Box::into_raw(content) as *mut _;
				let reactions = Box::into_raw(reactions) as *mut _;
				let mentions = Box::into_raw(mentions) as *mut _;

				let split = split.assume_init().offset_from(reactions as *mut _);
				let content = String::from_raw_parts(content, content_len, content_len);
				let reactions =
					Vec::from_raw_parts(reactions, reactions_len, reactions_len);
				let mentions =
					Vec::from_raw_parts(mentions, mentions_len, mentions_len);
				Ok((content, reactions, mentions, split as usize))
			},
			Some(error) => Err(error)
		}
	}
}

pub fn message_send(message: &str, channel: u64, reply: u64)
		-> Result<u64, NonZeroU8> {
	unsafe {
		let mut id = MaybeUninit::uninit();
		let result = raw::message_send(message.as_ptr(),
			message.len(), channel, reply, id.as_mut_ptr());

		match NonZeroU8::new(result) {
			None => Ok(id.assume_init()),
			Some(error) => Err(error)
		}
	}
}
