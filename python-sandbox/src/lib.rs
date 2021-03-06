#![feature(new_uninit)]

use rustpython_vm::{
	compile::Mode,
	pyobject::PyObjectRef,
	Interpreter,
	VirtualMachine
};
use std::mem::MaybeUninit;

// Why must I be a stranger in a world full of Python?

// Now with 20% more Undefined Behavior!

#[no_mangle]
pub extern fn main() -> usize {
	let code = read_code();
	Interpreter::default().enter(|vm| {
		let reply = vm.ctx.new_function("reply", |message: PyObjectRef, vm: &VirtualMachine| {
			let message = vm.to_repr(&message).unwrap();
			let message = message.as_ref();

			// Is Python unsafe? I don't know, probably.
			unsafe {
				let mut context = MaybeUninit::uninit();
				context_environment(context.as_mut_ptr());
				let context = context.assume_init();

				let mut id = MaybeUninit::uninit();
				let _ = message_send(message.as_ptr(), message.len(), context.channel_id, 0, id.as_mut_ptr());
			}
		});

		let code = vm.compile(&code, Mode::Exec, "/code.py".to_owned()).unwrap();
		let scope = vm.new_scope_with_builtins();

		vm.call_method(scope.globals.as_object(), "__setitem__", ("reply", reply))
			.expect("set error");
		vm.run_code_obj(code, scope).expect("exec error");
	});

	0
}

fn read_code() -> String {
	let data = Box::into_raw(Box::<[u8; 2000]>::new_uninit()) as *mut u8;

	// When the world of RustPython is burning, the world of CPython won't have a
	// care in the world.
	unsafe {
		let length = context_read_code(data);
		String::from_raw_parts(data, length, 2000)
	}
}

#[repr(C)]
struct ContextEnvironment {
	guild_id: u64,
	channel_id: u64,
	message_id: u64
}

#[link(wasm_import_module = "discord_bridge")]
extern "C" {
	fn context_read_code(buf: *mut u8) -> usize;

	/// Returns the Discord environment.
	///
	/// Parameters
	/// ----------
	/// #1: u64, ID of the guild.
	/// #2: u64, ID of the channel this interaction is in.
	/// #3: u64, ID of the message this interaction is triggered from.
	fn context_environment(env: *mut ContextEnvironment);

	/// Sends a message.
	///
	/// Paraeaters
	/// ----------
	/// #1: &str, Immutable pointer to message data.
	/// #2: u64, ID of the channel to send to.
	/// #3: u64, ID of the message to reply to, or 0.
	/// #4: &mut u64, Pointer to write the ID of the new message.
	///
	/// Returns
	/// -------
	/// #1: u8, Error number.
	/// 	0 for success.
	/// 	1 for message too long.
	/// 	2 for channel doesn't exist.
	/// 	3 for replied to message doesn't exist.
	/// 	4 for insufficient permissions.
	/// 	5 for unknown.
	fn message_send(msg: *const u8, msg_len: usize, channel: u64, reply: u64,
		id: *mut u64) -> u32;
}

/*struct TestObject {

}

impl PyClassDef for TestObject {
	const NAME: &'static str = "TestObject";
	const MODULE_NAME: Option<&'static str> = None;
	const TP_NAME: &'static str = "TestObject";
	const DOC: Option<&'static str> = None;
}*/
