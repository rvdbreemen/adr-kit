#![no_std]
#![no_main]

//! Minimal Windows process used only to measure the irreducible hook-launch
//! floor. It has no Rust standard library or C runtime.

use core::panic::PanicInfo;

#[link(name = "kernel32")]
unsafe extern "system" {
    fn ExitProcess(exit_code: u32) -> !;
}

#[unsafe(no_mangle)]
pub extern "system" fn mainCRTStartup() -> ! {
    unsafe { ExitProcess(0) }
}

#[panic_handler]
fn panic(_info: &PanicInfo) -> ! {
    unsafe { ExitProcess(0) }
}
