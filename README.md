# sst-save-editor
A reverse-engineered save editor for Space Simulation Toolkit.

You can install the library directly from PyPI:

```bash
pip install sst-save-editor
```

# Example scripts:

Loading, editing, and saving changes to a save file:

```python
from sst_save_editor import SaveManager

save = SaveManager(save="save.tar") # You can add an SST folder parameter, but it isn't required. It'd be like: SaveManager(save="save.tar", sst="C:\\path\\to\\sst")
save.load()

plutonium = save.materials.create_material(
    title="Plutonium", # Names the material "Plutonium"
    tag="Radioactive", # Places the material in a "Radioactive" category.
    properties={
        "maxValent": 8, # The material can have a maximum of 8 links.
        "rgb": [0.90, 0.90, 0.90, 1.0], # Gives the material a silvery color.
    }
)

print(plutonium) # Prints the ID of the newly created Plutonium.

uranium = save.materials.create_material(
    title="Uranium", # Names the material "Uranium"
    tag="Radioactive", # Places the material in a "Radioactive" category.
    properties={
        "maxValent": 8, # The material can have a maximum of 8 links.
        "rgb": [0.0, 1.0, 0.0, 1.0] # Gives the material a bright green color.
    }
)

print(uranium) # Prints the ID of the newly created Uranium.

# Create a reaction that simulates Plutonium's decay into Uranium:
id1, id2 = save.chemistry.add_symmetrical_reaction(
    source1=plutonium,
    source2=plutonium,
    result1=uranium,
    result2=plutonium,
    chance=1.0, # (Default)
    enabled=1 # (Default)
) # (You can also use add_reaction(), but you have to add the properties yourself.)

print(f"ID1: {id1}\nID2: {id2}") # Prints the ID of the first reaction, and the ID of the second reaction.
# add_symmetrical_reaction() exists due to a bug in SST which causes particles to only react in certain directions.
# It creates two reactions. One with the materials provided, and one where source1 and source2 (And their respective results) are swapped.
# This is just a workaround to the bug, it does not fix it.
# The bug is more visible at high chances.
# There is a modded SST build that somewhat solves this, but it is only available for wizards.

save.save() # Saves the changes to C:\Program Files (x86)\Steam\steamapps\common\Space Simulation Toolkit\saves\local\save.tar
```

Script that manually loads, edits, and saves changes to a save file:

```python
from sst_save_editor import Materials, Chemistry
save = "./save" # Assuming you've already extracted the save.
materials = Materials(folder=save)
materials.load_properties() # Load materials and their properties from the save.
materials.load_metadata() # Load material metadata from the save.

chemistry = Chemistry(folder=save)
chemistry.load_reactions() # Load reactions and their properties from the save.
chemistry.load_metadata() # Load reaction metadata from the save. (Metadata is currently broken, but it doesn't affect functionality.)

# Create a reaction which turns Water into Stone:
chemistry.add_reaction(properties={
    "source1": 2, # Water (ID 2)
    "source2": 2,
    "result1": 8, # Stone (ID 8)
    "result2": 8,
    "chance": 100.0, # High probability. (The aforementioned bug will show.)
    "enabled": 1 # (1 by default)
}) # This is the function that makes only one reaction.

materials.edit_metadata(material_id=0, tag="tag", value="Unused") # Changes the "tag" tag of the Default material (ID 0) to "Unused"
# It moves it to a category named "Unused" in the material menu.
materials.edit_material(material_id=0, property="rgb", value[1.0, 0.0, 1.0, 1.0]) # Gives the Default material a bright purple color.

# Save materials and their metadata back to the folder:
materials.save_properties()
materials.save_metadata()

# Save reactions and their metadata back to the folder:
chemistry.save_reactions()
chemistry.save_metadata()

# Then compress the folder back into tar and move it into the /saves/local folder in SST, and play!
```

Script that generates a wire with a material that emits rainbow waves:
```python
import colorsys # (For the colors)
from sst_save_editor import SaveManager

save = SaveManager("save.tar")
save.load() # Load the save from SST.

emitter = save.materials.create_material("Emitter", "Silly", {"maxValent": 0, "rgb": [1.0, 0.0, 0.0, 1.0]}) # Create the Emitter material.
wire = save.materials.create_material("Wire", "Silly", {"maxValent": 0, "rgb": [1.0, 1.0, 1.0, 1.0]}) # Create the Wire material.

COUNT = 100 # Create 100 different materials to travel down the wire.

for i in range(COUNT):
    hue = i / COUNT # Calculate the hue.
    r, g, b = colorsys.hsv_to_rgb(hue, 1.0, 1.0) # Convert it to RGB.
    rgb = [r, g, b, 1.0] # Define the RGB property for the material.

    material_id = save.materials.create_material(str(i), "", {"maxValent": 8, "rgb": rgb}) # Create the material for this current iteration, it has no category and 8 links.
    
    # If it's the last material:
    if i == COUNT - 1:
        # Make the emitter turn this wave material back into wire:
        save.chemistry.add_symmetrical_reaction(source1=emitter, source2=material_id, result1=emitter, result2=wire, chance=100)
        # Make the wire propagate into this wave material:
        save.chemistry.add_symmetrical_reaction(source1=material_id, source2=wire, result1=wire, result2=wire, chance=100)
        continue
    
    # If it's the first material:
    if i == 0:
        # Make the Emitter emit the wave.
        save.chemistry.add_symmetrical_reaction(source1=emitter, source2=wire, result1=emitter, result2=material_id, chance=100)
        # Make the Emitter turn this into the next wave material:
        save.chemistry.add_symmetrical_reaction(source1=emitter, source2=material_id, result1=emitter, result2=material_id + 1, chance=100)
        # Make this wave material propagate into the wire:
        save.chemistry.add_symmetrical_reaction(source1=material_id, source2=wire, result1=material_id, result2=material_id, chance=100)
        # Make the next wave material propagate into this one:
        save.chemistry.add_symmetrical_reaction(source1=material_id, source2=material_id + 1, result1=material_id + 1, result2=material_id + 1, chance=100)
        continue
    
    # Make the Emitter turn this wave material into the next wave material:
    save.chemistry.add_symmetrical_reaction(source1=emitter, source2=material_id, result1=emitter, result2=material_id + 1, chance=100)
    # Make the next wave material propagate into this one:
    save.chemistry.add_symmetrical_reaction(source1=material_id, source2=material_id + 1, result1=material_id + 1, result2=material_id + 1, chance=100)

save.save() # Save changes to the save file.
```
