import database

try:
    database.register_tool(
        name="Hammer",
        rfid_tag="T1234567",
        category="Hand Tool",
        condition="Good"
    )
    database.register_tool(
        name="Cordless Drill",
        rfid_tag="T2345678",
        category="Power Tool",
        condition="Fair"
    )
    database.register_tool(
        name="Ladder",
        rfid_tag="T3456789",
        category="Ladder",
        condition="Poor"
    )
    database.register_tool(
        name="Screwdriver Set",
        rfid_tag="T4567890",
        category="Hand Tool",
        condition="Good"
    )
    database.register_tool(
        name="Circular Saw",
        rfid_tag="T5678901",
        category="Power Tool",
        condition="Fair"
    )
    database.register_tool(
        name="Wrench Set",
        rfid_tag="T6789012",
        category="Hand Tool",
        condition="Good"
    )
    print("Sample tools registered successfully.")
except ValueError as e:
    print('Registration Failed:\n' + str(e))
