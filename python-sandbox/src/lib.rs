#![feature(new_uninit, test)]

mod api;

use self::api::scope;
use rustpython_vm::{compile::Mode, Interpreter};

// Why must I be a stranger in a world full of Python?

// Now with 20% more Undefined Behavior!

#[no_mangle]
pub extern fn main() -> usize {
	let code = read_code();
	Interpreter::default().enter(|vm| {
		let code = vm.compile(&code, Mode::Exec, "<embedded>".to_owned()).unwrap();
		let scope = scope(vm).unwrap();

		match vm.run_code_obj(code, scope) {
			Ok(_) => (),
			Err(error) => eprintln!("{}", vm.to_pystr(&error).unwrap())
		}
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

#[link(wasm_import_module = "discord_bridge")]
extern {
	fn context_read_code(data: *mut u8) -> usize;
}

/*struct TestObject {

}

impl PyClassDef for TestObject {
	const NAME: &'static str = "TestObject";
	const MODULE_NAME: Option<&'static str> = None;
	const TP_NAME: &'static str = "TestObject";
	const DOC: Option<&'static str> = None;
}*/
