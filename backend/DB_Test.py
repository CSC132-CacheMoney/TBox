import database
import pico_Reader

try:
    database.register_tool(
        name="Hammer",
        rfid_tag=pico_Reader.rand_Tool_ID(),
        category="Hand Tool",
        condition="Good"
    )
    database.register_tool(
        name="Cordless Drill",
        rfid_tag=pico_Reader.rand_Tool_ID(),
        category="Power Tool",
        condition="Fair"
    )
    database.register_tool(
        name="Ladder",
        rfid_tag=pico_Reader.rand_Tool_ID(),
        category="Ladder",
        condition="Poor"
    )
    database.register_tool(
        name="Screwdriver Set",
        rfid_tag=pico_Reader.rand_Tool_ID(),
        category="Hand Tool",
        condition="Good"
    )
    database.register_tool(
        name="Circular Saw",
        rfid_tag=pico_Reader.rand_Tool_ID(),
        category="Power Tool",
        condition="Fair"
    )
    database.register_tool(
        name="Wrench Set",
        rfid_tag=pico_Reader.rand_Tool_ID(),
        category="Hand Tool",
        condition="Good"
    )
    database.register_tool(
        name="Air Compressor",
        rfid_tag=pico_Reader.rand_Tool_ID(),
        category="Power Tool",
        condition="Poor"
    )
    database.register_tool(
        name="Extension Cord",
        rfid_tag=pico_Reader.rand_Tool_ID(),
        category="Accessory",
        condition="Good"
    )
    print("Sample tools registered successfully.")
except ValueError as e:
    print('Registration Failed:\n' + str(e))
