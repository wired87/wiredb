import json
from fractions import Fraction
import numpy as np



def is_complex(com):
    """
    Prüft rekursiv, ob ein Objekt komplexe Zahlen enthält.
    Gibt True zurück, sobald die erste komplexe Zahl gefunden wird.
    """
    try:
        # 1. Fall: Komplexe Zahl (Python, NumPy, JAX)
        if isinstance(com, (complex, np.complexfloating)):
            return True

        # 2. Fall: Bereits serialisiertes Dict {'real': ..., 'imag': ...}
        # Wir prüfen auf 'imag' != 0, falls du nur echte komplexe Werte filtern willst.
        # Falls JEDES serialisierte Dict als komplex gelten soll: 'real' in com and 'imag' in com
        if isinstance(com, dict) and 'real' in com and 'imag' in com:
            return True

        # 3. Fall: Listen, Tupel oder Arrays (Rekursiver Abstieg)
        if isinstance(com, (list, tuple, np.ndarray)):
            return any(is_complex(item) for item in com)

        # 4. Fall: Allgemeine Dictionaries (Metadaten durchsuchen)
        if isinstance(com, dict):
            return any(is_complex(v) for v in com.values())

        # 5. Fall: Basistypen (int, float)
        return False

    except Exception as e:
        print("Err is_complex", e)
        return False



def serialize_complex_dict(com, restore=False):
    """
    Verarbeitet rekursiv komplexe Zahlen, Matrizen und bereits
    existierende {'real': x, 'imag': y} Strukturen.
    """
    try:
        if restore:
            return deserialize_complex(com)

            # 1. Fall: Bereits serialisiertes Dict {'real': ..., 'imag': ...}
        if isinstance(com, dict) and 'real' in com:
            return com

            # 2. Fall: Komplexe Zahl (Python, NumPy, JAX)
        if isinstance(com, (complex, np.complexfloating)):
            return {"real": float(com.real), "imag": float(com.imag)}

            # 3. Fall: Arrays oder Listen (Rekursiver Abstieg)
            # Wichtig: Wir wandeln ALLES in eine Liste um und rufen uns selbst auf.
        if isinstance(com, (list, tuple, np.ndarray)):
            return [serialize_complex_dict(item) for item in com]

            # 4. Fall: Einzelne Zahlen (int, float, np.float64)
        if isinstance(com, (float, int, np.floating, np.integer)):
            return float(com)

            # 5. Fall: Allgemeine Dictionaries (z.B. Metadaten)
        if isinstance(com, dict):
            return {k: serialize_complex_process(v) for k, v in com.items()}

            # Wenn wir hier landen, ist es ein unbekannter Typ
        raise ValueError(f"Unknown serialize type: {type(com)} für Wert {com}")
    except Exception as e:
        print("Err serialize_complex_dict", e)


def deserialize_complex_dict(data):
    """ Wandelt die Dict-Struktur zurück in komplexe Zahlen """
    if isinstance(data, dict) and "real" in data and "imag" in data:
        return complex(data["real"], data["imag"])
    if isinstance(data, list):
        return [deserialize_complex(item) for item in data]
    if isinstance(data, dict):
        return {k: deserialize_complex(v) for k, v in data.items()}
    return data


def serialize_complex_process(com):
    """
    Serialisiert oder deserialisiert ein beliebig verschachteltes Array oder Listenstruktur.
    """
    try:
        if isinstance(com, (complex, np.complexfloating, np.complex128)):
            data = [float(com.real), float(com.imag)]

        elif isinstance(com, (list, tuple, np.ndarray)) and isinstance(com[0], (list, tuple, np.ndarray)):
            data = [serialize_complex_process(item) for item in com]

        elif isinstance(com, (list, tuple, np.ndarray)) and isinstance(com[0], (complex, np.complexfloating, np.complex128)):
            data = [[float(item.real), float(item.imag)] for item in com]

        elif isinstance(com, (list, tuple, np.ndarray)):
            # Handle empty array/list
            if len(com) == 0:
                data = []
            # numpy scalar types (np.int64, np.float32, etc.) - fix: Serialization error for ndarray
            elif isinstance(com[0], (float, int, np.integer, np.floating)):
                data = [float(item) for item in com]
            else:
                raise ValueError(f"Unknown serialize type, {com, type(com)}")

        else:
            raise ValueError(f"Unknown serialize type, {com, type(com)}")
        #print(">>>return admin_data", admin_data)
        return data

    except Exception as e:
        if isinstance(com, dict):
            for k,v in com.items():
                print(f"{k} type:", type(v))
        print("Serialization error", e, com)
    return com



def serialize_complex(com, restore=False, bytes=True):
    data = {"serialized_complex": serialize_complex_process(
        com, restore, bytes
    )}
    #print("After serialization:", admin_data)
    return data


def deserialize_complex(bytes_struct, from_json=True, key=None, **args):
    """
    Deserialisiert ein einzelnes oder verschachteltes serialisiertes Array.
    """

    #LOGGER.info(f"bytes_struct {bytes_struct}")
    #LOGGER.info(f"key {key}")
    #print("Deserialize:", bytes_struct)
    try:
        # Falls String, erst JSON laden
        if from_json and isinstance(bytes_struct, str):
            bytes_struct = json.loads(bytes_struct)

        if isinstance(bytes_struct, dict):
            bytes_struct = bytes_struct["serialized_complex"]
        if (
                isinstance(bytes_struct, list)
                and len(bytes_struct) == 2
                and all(isinstance(x, (int, float)) for x in bytes_struct)
        ):
            #print(" len(bytes_struct) == 2 v  bytes_struct", bytes_struct)
            restored = np.complex128(complex(bytes_struct[0], bytes_struct[1])) #restored = np.complex128(complex(bytes_struct[0] + bytes_struct[1]))

        elif isinstance(bytes_struct, list) and isinstance(bytes_struct[0], list):
            restored = np.array([deserialize_complex(item) for item in bytes_struct])

        else:
            restored = bytes_struct
        #print(f"deserialized complex: {restored}")
        return restored
    except Exception as e:
        print("Error deserialize struct", e)

def check_serilisation(data):
    # is admin_data serializable?
    try:
        # yes:
        json.dumps(data)
        return data
    except Exception as e:
        # no -> serialize

        #LOGGER.info(f"Serialisation Error: {e}")
        serialized = serialize_complex(data)
        #print(">>serialized", serialized)
        return serialized

def convert_numeric(v):
    try:
        return Fraction(v)
    except Exception as e:
        return v


def check_serialize_dict(data, attr_keys=None):
    # why attr_keys? -> serialize self.__dict__
    try:
        new_dict={}
        for k, v in data.items():
            if attr_keys is not None:
                if k in attr_keys:
                    #print("Convert sd key:", k, type(v), v)
                    v = check_serilisation(v)
                    new_dict[k] = v
            else:
                # print("Convert sd key:", k, type(v), v)
                v = check_serilisation(v)
                new_dict[k] = v
        return new_dict
    except Exception as e:
        print("Error serialize dict", e)
        return data
