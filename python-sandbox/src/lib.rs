#![feature(new_uninit)]

use rustpython_vm::{
	builtins::PyStr,
	compile::Mode,
	pyobject::PyRef,
	Interpreter
};

#[no_mangle]
pub extern fn main() -> usize {
	let code = read_code();
	Interpreter::default().enter(|vm| {
		let reply = vm.ctx.new_function("reply", |message: PyRef<PyStr>| {
			let message = message.as_ref();
			// Why must I be a stranger in a world full of Python?

			// Now with 20% more Undefined Behavior!

			// Is Python unsafe? I don't know, probably.
			unsafe {message_reply(message.as_ptr(), message.len())};
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

extern {
	fn context_read_code(buf: *mut u8) -> usize;
	fn message_reply(msg: *const u8, msg_len: usize);
}

/*struct TestObject {

}

impl PyClassDef for TestObject {
	const NAME: &'static str = "TestObject";
	const MODULE_NAME: Option<&'static str> = None;
	const TP_NAME: &'static str = "TestObject";
	const DOC: Option<&'static str> = None;
}*/
