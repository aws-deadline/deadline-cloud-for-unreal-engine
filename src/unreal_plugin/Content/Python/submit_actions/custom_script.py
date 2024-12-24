# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

# Simple script that just execute computation of unreal Vectors


def main():
    import unreal

    unreal.log("Executing Custom Script ...")

    v1 = unreal.Vector()
    v1.x = 10
    unreal.log(f"Vector 1: {v1.x}, {v1.y}, {v1.z}")

    v2 = unreal.Vector(10, 20, 30)
    unreal.log(f"Vector 2: {v2.x}, {v2.y}, {v2.z}")

    v3 = (v1 + v2) * 2
    unreal.log(f"Resulted Vector 3: {v3.x}, {v3.y}, {v3.z}")
