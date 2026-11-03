import tarfile
import shutil
import json
import os
import gzip
import struct
from pathlib import Path

class Materials:
    def __init__(self, folder):
        self.folder = folder
        self.properties = {}
        self.metadata = {}

        self.FLOAT_PROPERTIES = {
            "add_linked", "add_temp", "aquacap", "aquacond", "arobust",
            "cdist", "cpow", "csize", "csizemul", "damp", "gravity",
            "hdiff", "hdiff2", "ldamp", "lpow", "lrobust", "mass", "phototemp",
            "rgb", "tcond", "tdistmax", "tpowmax", "max_stuck", "electroheat",
            "electrocap", "electrocond", "electrophotomass", "sangle", "electroforce",
            "electrotonus", "frct", "attr", "xeno", "magnetic", "tdist", "tpow",
            "cde_heat", "racap", "racond", "add_aqua", "tphase"
        }

        self.STRIDE_MAP = {
            "dragpos": 2,
            "rgb": 4,
            "tfire": 4,
            "tphase": 2,
            "mphase": 2,
            "vphase": 2
        }
    
    def _get_format_character(self, property):
        if property in self.FLOAT_PROPERTIES:
            return "f"
        else:
            return "i"

    def load_properties(self):
        print(f"Loading properties from {self.folder}...")
        for property_file in Path(f"{self.folder}\\dump\\Cosmos\\Material").glob("*.prop"):
            property = property_file.stem

            with gzip.open(property_file, "rb") as f:
                binary = f.read()
            
            numbers = len(binary) // 4
            stride = self.STRIDE_MAP.get(property, 1)
            type_character = self._get_format_character(property)
            format = f"<{numbers}{type_character}"
            
            raw_values = struct.unpack(format, binary)

            if stride == 1:
                if type_character == "f":
                    self.properties[property] = [round(value, 5) for value in raw_values]
                    print(f"Loaded {property} with {len(self.properties[property])} entries!")
                else:
                    self.properties[property] = list(raw_values)
                    print(f"Loaded {property} with {len(self.properties[property])} entries!")
            else:
                list_property = []
                for i in range(0, len(raw_values), stride):
                    chunk = raw_values[i:i + stride]
                    if type_character == "f":
                        chunk = [round(v, 5) for v in chunk]
                    list_property.append(list(chunk))
                self.properties[property] = list_property
                print(f"Loaded {property} with {len(self.properties[property])} entries!")
        
        print(f"Loaded {len(self.properties)} properties from {self.folder}.")

    def load_metadata(self):
        print(f"Loading material metadata from {self.folder}...")
        metadata_path = Path(f"{self.folder}\\dump\\Cosmos\\Material\\vars.json")
        if metadata_path.exists():
            with open(metadata_path, "r", encoding="utf-8") as f:
                self.metadata = json.load(f)
            print("Loaded material metadata!")
        else:
            print("Material metadata not found!")

    def find_by_uid(self, uid):
        if not self.metadata:
            print("Material metadata not loaded!")
            return None
            
        reftext = self.metadata.get("$REFTEXT", [])
        
        for index, entry in enumerate(reftext):
            if isinstance(entry, dict):
                if "item" in entry and entry["item"].get("uid", 0) == uid:
                    return index

    def create_material(self, title=None, tag=None, properties=None, base=0):
        if not self.metadata or not self.properties:
            print("You must load both properties and material metadata first!")
            return None

        if properties is None:
            properties = {}

        reftext = self.metadata.get("$REFTEXT", [])
        id = len(reftext)

        for property, values_list in self.properties.items():
            stride = self.STRIDE_MAP.get(property, 1)
            type_character = self._get_format_character(property)
            if len(values_list) > base:
                default = values_list[base]
            elif len(values_list) > 0:
                default = values_list[0]
            else:
                default = [0.0 if type_character == "f" else 0] * stride if stride > 1 else (0.0 if type_character == "f" else 0)
       
            default = default[:] if isinstance(default, list) else default
            
            if property in ["__ar", "__ra"]:
                values_list.append(id)
                continue
            elif property.startswith("__"):
                values_list.append(0)
                continue

            if property in properties and properties[property] is not None:
                value = properties[property]

                if value is not None:
                    if stride == 1:
                        if isinstance(value, (int, float)):
                            value = float(value) if type_character == "f" else int(value)
                        else:
                            print(f"[{property}] Expected a number, got {type(value).__name__}. Defaulting to Material 0.")
                            value = default
                    else:
                        if (isinstance(value, list) and 
                            len(value) == stride and 
                            all(isinstance(v, (int, float)) for v in value)):
                            
                            value = [float(v) if type_character == "f" else int(v) for v in value]
                        else:
                            print(f"[{property}] Invalid list format or length (Expected {stride} numbers). Defaulting to Material 0.")
                            value = default
                values_list.append(value)
            else:
                value = default

                values_list.append(value)

        base_metadata = self.get_metadata(base)

        entry = {
            "title": title if title else base_metadata["title"],
            "tag": tag if tag else base_metadata["tag"],
            "color": base_metadata["color"],
            "invert": 1,
            "icon": base_metadata["icon"],
            "item": {
                "uid": id,
                "title": title if title else base_metadata["title"],
                "icon": base_metadata["icon"],
                "color": base_metadata["color"],
                "active": 1
            }
        }

        reftext.append(entry)

        self.metadata["acount"] = len(reftext)
        self.metadata["count"] = len(reftext)

        print(f"Successfully created \"{title}\" at Material ID {id}!")
        return id

    def get_properties(self, material_id):
        material = {"id": material_id}
        for property, values in self.properties.items():
            if material_id < len(values):
                material[property] = values[material_id]
            else:
                material[property] = None
        return material
    
    def get_metadata(self, material_id):
        if not self.metadata:
            print(f"Material metadata has not been loaded yet! Run load_metadata() first!")
            return None

        reftext = self.metadata.get("$REFTEXT", [])

        if 0 <= material_id < len(reftext):
            entry = reftext[material_id]

            if isinstance(entry, str):
                return {
                    "title": entry,
                    "tag": "None",
                    "color": "#FFFFFFFF",
                    "icon": "None",
                    "is_placeholder": True
                }
            return entry
        else:
            print(f"ID {material_id} out of bounds! (Range: 0 to {len(reftext) - 1})")
            return None
    
    def edit_metadata(self, material_id, tag, value):
        if not self.metadata:
            print(f"Material metadata has not been loaded yet! Run load_metadata() first!")
            return None
        
        reftext = self.metadata.get("$REFTEXT", [])

        if 0 <= material_id < len((reftext)):
            reftext[material_id][tag] = value
        else:
            print(f"ID {material_id} out of bounds! (Range: 0 to {len(reftext) - 1})")
            return None
        
    def edit_material(self, material_id, property, value):
        if property in self.properties:
            if 0 <= material_id < len(self.properties[property]):
                self.properties[property][material_id] = value
                print(f"Material {material_id} {property} updated to {value}.")
            else:
                print(f"ID {material_id} out of bounds! (Range: 0 - {len(self.properties[property]) - 1})")
        else:
            print(f"Property {property} does not exist!")
    
    def save_properties(self):
        print("Saving all properties...")
        for property, values in self.properties.items():
            file = Path(f"{self.folder}\\dump\\Cosmos\\Material\\{property}.prop")
            stride = self.STRIDE_MAP.get(property, 1)

            if not stride == 1:
                values = [val for chunk in values for val in chunk]

            type_character = self._get_format_character(property)
            format = f"<{len(values)}{type_character}"
            binary = struct.pack(format, *values)

            with gzip.open(file, "wb") as f:
                f.write(binary)
        
        print("Properties saved!")

    def save_metadata(self):
        print("Saving material metadata...")
        with open(Path(f"{self.folder}\\dump\\Cosmos\\Material\\vars.json"), "w") as f:
            json.dump(self.metadata, f, indent=4)
        print(f"Material metadata saved!")

class Chemistry:
    def __init__(self, folder):
        self.folder = folder
        self.properties = {}
        self.metadata = {}
        self.INT_PROPERTIES = {
            "enabled", "result1", "result2", "source1",
            "source2", "__de", "__eq", "__ho", "__ra", "__ar", "__rev__Cosmos__Material_reactions1",
            "__rev__Cosmos__Material_reactions2", "overflow", "aqua_cond", "electro_cond",
            "pressure_cond", "ra_cond", "temp_cond"
        }
        self.STRIDE_MAP = {
            "dragpos": 2
        }

    def _get_format_character(self, property):
        if property in self.INT_PROPERTIES or property.startswith("__"):
            return "i"
        else:
            return "f"

    def load_reactions(self):
        print(f"Loading reaction properties from {self.folder}...")
        for property_file in Path(f"{self.folder}\\dump\\Cosmos\\React").glob("*.prop"):
            property = property_file.stem
            with gzip.open(property_file, "rb") as f:
                binary = f.read()
            
            numbers = len(binary) // 4
            stride = self.STRIDE_MAP.get(property, 1)
            type_character = self._get_format_character(property)
            format = f"<{numbers}{type_character}"
            
            raw_values = struct.unpack(format, binary)

            if stride == 1:
                if type_character == "f":
                    self.properties[property] = [round(v, 5) for v in raw_values]
                else:
                    self.properties[property] = list(raw_values)
            else:
                list_property = []
                for i in range(0, len(raw_values), stride):
                    chunk = raw_values[i:i + stride]
                    if type_character == "f":
                        chunk = [round(v, 5) for v in chunk]
                    list_property.append(list(chunk))
                self.properties[property] = list_property

            print(f"Loaded {property} with {len(self.properties[property])} entries.")

        print(f"Successfully loaded {len(self.properties)} reaction properties!")

    def load_metadata(self):
        print(f"Loading reaction metadata from {self.folder}...")
        metadata_path = Path(f"{self.folder}\\dump\\Cosmos\\React\\vars.json")
        if metadata_path.exists():
            with open(metadata_path, "r", encoding="utf-8") as f:
                self.metadata = json.load(f)

            acount = self.metadata.get("acount", 0)
            reftext = self.metadata.get("$REFTEXT", [])
            
            if len(reftext) > acount:
                self.metadata["$REFTEXT"] = reftext[:acount]

            print("Loaded reaction metadata!")
        else:
            print("Reaction metadata not found!")

    def get_properties(self, reaction_id):
        reaction = {"id": reaction_id}
        for property, values in self.properties.items():
            if reaction_id < len(values):
                reaction[property] = values[reaction_id]
            else:
                reaction[property] = None
        return reaction
    
    def add_reaction(self, properties=None):
        if properties is None:
            properties = {}

        id = len(self.properties.get("__ar", []))

        for property, values_list in self.properties.items():
            stride = self.STRIDE_MAP.get(property, 1)
            type_character = self._get_format_character(property)
            
            if property in ["__ar", "__ra"]:
                values_list.append(id)
                continue
            elif property.startswith("__"):
                values_list.append(0)
                continue
            elif property == "enabled":
                values_list.append(1)
                continue
            elif property == "chance":
                values_list.append(100)
                continue

            if stride == 1:
                default = 0.0 if type_character == "f" else 0
            else:
                default = [0.0 if type_character == "f" else 0 for _ in range(stride)]
            
            if property in properties and properties[property] is not None:
                value = properties[property]

                if stride == 1:
                    if isinstance(value, (int, float)):
                        value = float(value) if type_character == "f" else int(value)
                    else:
                        print(f"[{property}] Expected a number, got {type(value).__name__}. Defaulting to 0")
                        value = default
                else:
                    if (isinstance(value, list) and 
                        len(value) == stride and 
                        all(isinstance(v, (int, float)) for v in value)):
                        
                        value = [float(v) if type_character == "f" else int(v) for v in value]
                    else:
                        print(f"[{property}] Invalid list format or length. Defaulting to 0.")
                        value = default
            else:
                value = default

            values_list.append(value)

        reftext = self.metadata.get("$REFTEXT", [])
        
        reaction_properties = self.get_properties(id)

        entry = {
            "title": f"{reaction_properties["source1"]} + {reaction_properties["source2"]} => {reaction_properties["result1"]} + {reaction_properties["result2"]}",
            "icon": "fa_flask",
            "color": "#CCCC77FF",
            "invert": 1
        }

        reftext.append(entry)
        
        self.metadata["acount"] = len(reftext)
        self.metadata["count"] = len(reftext)

        print(f"Successfully created reaction at ID {id}!")
        return id
    
    def add_symmetrical_reaction(self, source1=0, source2=0, result1=0, result2=0, chance=1.0, enabled=1):
        id1 = self.add_reaction({
            "source1": source1,
            "source2": source2,
            "result1": result1,
            "result2": result2,
            "chance": chance,
            "enabled": enabled
        })
        id2 = self.add_reaction({
            "source1": source2,
            "source2": source1,
            "result1": result2,
            "result2": result1,
            "chance": chance,
            "enabled": enabled
        })

        return id1, id2

    def edit_reaction(self, reaction_id, property, value):
        if property in self.properties:
            if 0 <= reaction_id < len(self.properties[property]):
                self.properties[property][reaction_id] = value
                print(f"Reaction {reaction_id} {property} updated to {value}.")
            else:
                print(f"ID {reaction_id} out of bounds!")
        else:
            print(f"Property {property} not found!")

    def edit_metadata(self, reaction_id, tag, value):
        if not self.metadata:
            print(f"Reaction metadata has not been loaded yet! Run load_metadata() first!")
            return None
        
        reftext = self.metadata.get("$REFTEXT", [])

        if 0 <= reaction_id < len(reftext):
            reftext[reaction_id][tag] = value
        else:
            print(f"ID {reaction_id} out of bounds! (Range: 0 to {len(reftext) - 1})")
            return None

    def save_reactions(self):
        print("Saving reactions...")
        for property, values in self.properties.items():
            stride = self.STRIDE_MAP.get(property, 1)

            if not stride == 1:
                values = [val for chunk in values for val in chunk]
            else:
                values = values

            type_character = self._get_format_character(property)
            format = f"<{len(values)}{type_character}"
            binary = struct.pack(format, *values)

            with gzip.open(Path(f"{self.folder}\\dump\\Cosmos\\React\\{property}.prop"), "wb") as f:
                f.write(binary)
                
        print("Reactions saved!")

    def save_metadata(self):
        print("Saving reaction metadata...")
        with open(Path(f"{self.folder}\\dump\\Cosmos\\React\\vars.json"), "w") as f:
            json.dump(self.metadata, f, indent=4)
        print(f"Reaction metadata saved!")

class SaveManager:
    def __init__(self, save=None, sst="C:\\Program Files (x86)\\Steam\\steamapps\\common\\Space Simulation Toolkit"):
        if save is None:
            print("You have not provided a save!")
            self.save_name = None
        else:
            self.save_name = Path(save)
        self.script_cache = Path("./_save_cache")
        self.sst = Path(sst)
        self.materials = None
        self.chemistry = None

    def load_folder(self):
        self.materials = Materials(Path(f"{self.script_cache}\\{self.save_name.stem}"))
        self.chemistry = Chemistry(Path(f"{self.script_cache}\\{self.save_name.stem}"))

        self.materials.load_properties()
        self.materials.load_metadata()
        self.chemistry.load_reactions()

        print("Folder fully loaded into memory!")
        return True

    def load(self, clear_temp=True):
        print(f"Extracting {self.save_name} to temporary workspace...")

        if self.script_cache.exists() and clear_temp == True:
            shutil.rmtree(self.script_cache)
            """elif self.script_cache.exists() and clear_temp == False:
            self.materials = Materials(Path(f"{self.script_cache}\\{self.save_name.stem}"))

            self.materials.load_properties()
            self.materials.load_metadata()

            print("Save file fully loaded into memory!")
            return True"""
        else:
            self.script_cache.mkdir(parents=True, exist_ok=True)

        if Path(f"{self.sst}\\saves\\local\\{self.save_name}").exists():
            with tarfile.open(Path(f"{self.sst}\\saves\\local\\{self.save_name}"), "r") as tar:
                tar.extractall(path=Path(f"{self.script_cache}\\{self.save_name.stem}"))
        else:
            print("Save files not found!")
            return False
        
        self.materials = Materials(Path(f"{self.script_cache}\\{self.save_name.stem}"))
        self.chemistry = Chemistry(Path(f"{self.script_cache}\\{self.save_name.stem}"))


        self.materials.load_properties()
        self.materials.load_metadata()
        self.chemistry.load_reactions()
        self.chemistry.load_metadata()
        
        print("Save file fully loaded into memory!")
        return True

    def save(self, output_path=None, clear_temp=True, clear_cache=None):
        if output_path is None:
            output_path = Path(f"{self.sst}\\saves\\local\\{self.save_name}")
            if clear_cache is None: clear_cache = True
        else:
            if clear_cache is None: clear_cache = False
        
        print("Committing changes to temporary workspace...")

        self.materials.save_properties()
        self.materials.save_metadata()
        self.chemistry.save_reactions()
        self.chemistry.save_metadata()

        print(f"Recompressing into {output_path}...")
        with tarfile.open(output_path, "w") as tar:
            for file in Path(f"{self.script_cache}\\{self.save_name.stem}").iterdir():
                tar.add(file, arcname=file.name)
        
        if Path(f"{self.script_cache}\\{self.save_name.stem}").exists() and clear_temp == True:
            shutil.rmtree(Path(f"{self.script_cache}\\{self.save_name.stem}"))

        if clear_cache == True and Path(f"{self.sst}\\cache\\saves\\local\\{self.save_name.stem}").exists():
            print("Clearing game cache...")
            shutil.rmtree(Path(f"{self.sst}\\cache\\saves\\local\\{self.save_name.stem}"))
            print("Game cache successfully cleared!")
        elif clear_cache == True and not Path(f"{self.sst}\\cache\\saves\\local\\{self.save_name.stem}").exists():
            print(f"Save at {Path(f"{self.sst}\\cache\\saves\\local\\{self.save_name.stem}")} has not been found. Either the cache has already been cleared, or your path is wrong.")

        print("Save complete!")
