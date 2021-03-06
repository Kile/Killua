use discord_bridge::{
	raw::Message,
	context_environment,
	message_load
};
use rustpython_vm::{
	builtins::{PyDict, PyStr, PyType},
	function::{FuncArgs, IntoPyNativeFunc},
	pyobject::{PyObjectRef, PyRef, PyResult, PyValue},
	scope::Scope,
	slots::PyTypeSlots,
	VirtualMachine
};
use std::collections::HashMap;

pub fn scope(vm: &VirtualMachine) -> PyResult<Scope> {
	let mut globals = HashMap::new();

	let message_class = PyMessage::new_class(vm);
	let message_class_object = message_class.clone().into_object();
	globals.insert(message_class.name.clone(), message_class_object);

	let message_function = NativeLiteral::new(fetch_message, message_class);
	let message_function = vm.ctx.new_function("message", message_function);
	globals.insert("message".to_owned(), message_function);

	Ok(Scope::with_builtins(None, to_dict(vm, globals)?, vm))
}

fn to_dict(vm: &VirtualMachine, map: HashMap<String, PyObjectRef>)
		-> PyResult<PyRef<PyDict>> {
	let dict = vm.ctx.new_dict();
	let object = dict.as_object();

	map.into_iter()
		.try_for_each(|entry|
			vm.call_method(object, "__setitem__", entry).map(|_| ()))?;
	Ok(dict)
}

struct NativeLiteral<T>
		where T: Send + Sync + 'static {
	function: fn(data: &T, vm: &VirtualMachine, args: FuncArgs) -> PyResult,
	data: T
}

impl<T> NativeLiteral<T>
		where T: Send + Sync + 'static {
	fn new(
		function: fn(data: &T, vm: &VirtualMachine, args: FuncArgs) -> PyResult,
		data: T
	) -> Self {
		Self {function, data}
	}
}

impl<T> IntoPyNativeFunc<()> for NativeLiteral<T>
		where T: Send + Sync + 'static {
	fn call(&self, vm: &VirtualMachine, args: FuncArgs) -> PyResult {
		(self.function)(&self.data, vm, args)
	}
}

#[derive(Debug)]
struct PyMessage {
	data: Message
}

fn fetch_message(ty: &PyRef<PyType>, _: &VirtualMachine, _: FuncArgs)
		-> PyResult {
	let (_, channel, _) = context_environment();
	match message_load(1, channel, 0) {
		Ok(messages) => {
			let payload = PyMessage {data: messages[0]};
			Ok(PyRef::new_ref(payload, ty.clone(), None).into_object())
		},
		Err(_) => panic!()
	}
}

impl PyMessage {
	fn new_class(vm: &VirtualMachine) -> PyRef<PyType> {
		let object = vm.get_attribute(vm.builtins.clone(), "object")
			.unwrap().downcast().unwrap();

		let mut class = PyTypeSlots::default();
		class.new = Some(Box::new(Self::new));
		class.getattro.swap(Some(Self::get_attribute));
		vm.ctx.new_class("Message", &object, class)
	}

	fn new(vm: &VirtualMachine, args: FuncArgs) -> PyResult {
		let ty = args.args[0].clone().downcast::<PyType>().unwrap();
		let message = format!("{:?} cannot be instantiated directly", ty.name);
		Err(vm.new_type_error(message))
	}

	fn get_attribute(this: PyObjectRef, key: PyRef<PyStr>, vm: &VirtualMachine)
			-> PyResult {
		let this = this.downcast::<PyMessage>()
			.map_err(|_| vm.new_type_error("bad".to_owned()))?;

		match key.as_ref() {
			"id" => Ok(vm.ctx.new_int(this.data.id)),
			key => {
				let message = format!("object has no attribute {:?}", key);
				Err(vm.new_attribute_error(message))
			}
		}
	}
}

impl PyValue for PyMessage {
	//unsafe {std::mem::transmute(vm.get_attribute(vm.builtins.clone(), "Test").unwrap().downcast_ref::<PyType>().unwrap())}
	fn class(_: &VirtualMachine) -> &PyRef<PyType> {
		unimplemented!()
	}
}

/*let reply = vm.ctx.new_function("reply", |message: PyObjectRef, vm: &VirtualMachine| {
	let message = vm.to_repr(&message).unwrap();
	let message = message.as_ref();

	// Is Python unsafe? I don't know, probably.
	unsafe {
		panic!()
	}
});*/
