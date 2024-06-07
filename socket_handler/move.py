import epics
import argparse

bl_x_center = epics.PV("BL04I-DI-OAV-01:OVER:1:CenterX")
bl_y_center = epics.PV("BL04I-DI-OAV-01:OVER:1:CenterY")

x_center = epics.PV("rpi:MXSC:TipX")
y_center = epics.PV("rpi:MXSC:TipY")

def main():
    parser=argparse.ArgumentParser(description="add murko overlay")

    parser.add_argument('x', type=int, help="x coord") 
    parser.add_argument('y', type=int, help="y coord") 
    args = parser.parse_args()

    result = move_to_position(args.x,args.y)

def move_to_position(x, y):
    bl_x_center.put(x)
    bl_y_center.put(y)

if __name__ == "__main__":
    main()
