use rustpython_vm::{
	builtins::PyStr,
	compile::Mode,
	pyobject::PyRef,
	Interpreter
};

#[no_mangle]
pub extern fn main() -> usize {
	let interpreter = Interpreter::default();

	/*println!("{:?}", rustpython_vm::builtins::PyDict::NAME);
	println!("{:?}", rustpython_vm::builtins::PyDict::MODULE_NAME);
	println!("{:?}", rustpython_vm::builtins::PyDict::TP_NAME);
	println!("{:?}", rustpython_vm::builtins::PyDict::DOC);*/

	interpreter.enter(|vm| {
		let my_fn = vm.ctx.new_function("my_fn", |message: PyRef<PyStr>| {
			let message = message.as_ref();
			// Why must I be a stranger in a world full of Python?

			// Now with 20% more Undefined Behavior!

			// When the world of RustPython is burning, the world of CPython won't
			// have a care in the world.

			// Is Python unsafe? I don't know, probably.
			unsafe {message_reply(message.as_ptr(), message.len())};
			println!("Rusting! {}", message);
		});

		let code = vm.compile("print(\"hello, amazing beautiful world!\")\nmy_fn(\"beautiful!\")", Mode::Exec, "/code.py".to_owned()).unwrap();
		let scope = vm.new_scope_with_builtins();

		vm.call_method(scope.globals.as_object(), "__setitem__", ("my_fn", my_fn))
			.expect("set error");
		//vm.set_attr(scope.globals.as_object(), "my_fn", my_fn).expect("set error");

		vm.run_code_obj(code, scope).expect("exec error");
	});

	0
}

extern {
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
