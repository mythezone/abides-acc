import dearpygui.dearpygui as dpg

dpg.create_context()
dpg.create_viewport(title="CALIBRAX Simulator", width=800, height=600)


with dpg.window(label="CALIBRAX"):
    dpg.add_text("Welcome to CALIBRAX Simulator!")
    dpg.add_button(
        label="Start Simulation", callback=lambda: print("Simulation started!")
    )
    dpg.add_button(
        label="Stop Simulation", callback=lambda: print("Simulation stopped!")
    )
    dpg.add_input_text(label="Enter command", hint="Type your command here")
    dpg.add_checkbox(label="Enable Debug Mode")

dpg.setup_dearpygui()
dpg.show_viewport()
dpg.start_dearpygui()
dpg.destroy_context()
