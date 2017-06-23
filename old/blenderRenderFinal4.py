import bpy
import math
import sys
import json

bpy.ops.object.select_all()
bpy.ops.object.delete()
bpy.context.scene.render.engine = 'CYCLES'
start_frame=0
end_frame=0
camOpInput=open(sys.argv[4],'r')

# Uses the user specified input
class camOptions():
  def __init__(self):
     self.predefinedView=True
     # If predefinedView=False
     self.focusPoint=(0,0,0)
     self.camLocation=(0,0,0)
     # Else:
     # Camera orientation:
     # iso, front, back, top, bottom, left, right
     self.orientation='iso'
     # Camera distance
     # Zero value will trigger the default option
     self.distance=0
     # Camera will towards its focus point
     # Chose shell or mainObject
     # shell: Boundary of the domain
     # mainObject: imported volume
     self.focus='shell'
  def setLocations(self,focusOb):
     if self.predefinedView:
        shellSize=focusOb.dimensions
        shellLocation=focusOb.matrix_world.to_translation()
        p1=-(shellLocation[0]+shellSize[0])/2
        p2=(shellLocation[1]+shellSize[1])/2
        p3=(shellLocation[2]+shellSize[2])/2
        self.focusPoint=(p1,p2,p3)
        if self.distance==0:
           self.distance=7*max(shellLocation[0]+shellSize[0],shellLocation[1]+shellSize[1],shellLocation[2]+shellSize[2])
        self.camLocation=(p1,p2,self.distance)
        if self.orientation=='iso':
           cos45=math.cos(math.pi/4)
           self.camLocation=(self.distance*cos45,self.distance*cos45,self.distance*cos45)
        elif self.orientation=='front':
           self.camLocation=(p1,p2,self.distance)
        elif self.orientation=='back':
           self.camLocation=(p1,p2,-self.distance)
        elif self.orientation=='right':
           self.camLocation=(p1,self.distance,p3)
        elif self.orientation=='left':
           self.camLocation=(p1,-self.distance,p3)
        elif self.orientation=='up':
           self.camLocation=(-self.distance,p2,p3)
        elif self.orientation=='down':
           self.camLocation=(self.distance,p2,p3)
        
        
def assignColorMaterial(diffuse, specular, alpha, ob):
    mat = bpy.data.materials.new('colorMat')
    mat.diffuse_color = diffuse
    mat.diffuse_shader = 'LAMBERT'
    mat.diffuse_intensity = 1.0
    mat.specular_color = specular
    mat.specular_shader = 'COOKTORR'
    mat.specular_intensity = 0.5
    mat.alpha = alpha
    mat.ambient = 1
    setMaterial(ob,mat)
    return ob


# MAKE NODE-BASED MATERIAL FOR CYCLES_RENDER
def assignGlassMaterial(glassObject):
    bpy.context.scene.objects.active = None
    bpy.context.scene.objects.active=glassObject 
    mat=bpy.data.materials.new(name="Glass")
    setMaterial(glassObject,mat)
    cmat=glassObject.active_material
    cmat.use_nodes=True
    TreeNodes=cmat.node_tree
    links = TreeNodes.links
    # Remove nodes (clean it)
    for node in TreeNodes.nodes:
        TreeNodes.nodes.remove(node)
    # Add the guy to the node view
    # Output node
    node_out = TreeNodes.nodes.new(type='ShaderNodeOutputMaterial')
    node_out.location = 200,0
    # Toon
    #node_Toon = TreeNodes.nodes.new(type='ShaderNodeBsdfTransparent')
    node_Toon = TreeNodes.nodes.new(type='ShaderNodeBsdfGlass')
    node_Toon.location = 0,0
    # Activate to select color
    #node_Toon.inputs[0].default_value = (0.488,0.66,0.58,1)  # green RGBA
    node_Toon.inputs[1].default_value = 0.00  
    node_Toon.inputs[2].default_value = 0.00 
    # Connect the guys
    links.new(node_Toon.outputs[0], node_out.inputs[0])
    return glassObject

def assignWaterMaterial(waterObject):
    bpy.context.scene.objects.active = None
    bpy.context.scene.objects.active=waterObject
    mat = bpy.data.materials.new(name="Water")
    setMaterial(waterObject,mat)
    cmat=waterObject.active_material
    cmat.use_nodes=True
    TreeNodes=cmat.node_tree
    links = TreeNodes.links
    for node in TreeNodes.nodes:
        TreeNodes.nodes.remove(node)
    node_out = TreeNodes.nodes.new(type='ShaderNodeOutputMaterial')
    node_out.location = 200,0
    node_glass = TreeNodes.nodes.new(type='ShaderNodeBsdfGlass')
    node_glass.location =0,180
    node_glass.distribution = 'GGX'
    node_glass.inputs['Color'].default_value= (0.619,0.727,0.8,1)
    node_glass.inputs['Roughness'].default_value=0.34
    links.new(node_glass.outputs[0], node_out.inputs[0])
    return waterObject


def setMaterial(ob, mat):
    me = ob.data
    if len(me.materials):
       ob.data.materials[0] = mat
    else:
        ob.data.materials.append(mat)
    return ob 


## This class stores and updates the position of the camera
# Note 1: The process of updating the camera position is not affected by its previous position
# Note 2: The function will only work if the following options are selected for importing the mesh:
#         axis_forward='X', axis_up='Z'. Otherwise, changes need to be made to it.          
class camPosition():
  def __init__(self):
     # Distance in the (y,z) plane from the camLocation to focusPoint
     self.radius=0
     # Distance to the (y,z) plane along the x axis
     self.height=0
     # The angles are defined using the aircraft convention where the
     # (y,z) plane is the ground and x is the vertical axis
     self.yaw=0
     self.pitch=0
     self.roll=math.pi/2
  # Sets the camera position to camLocation and modifies its angles
  # so that it is looking towards focusPoint
  # External Input
  # - focusPoint: The camera will be looking at this point
  # - camLocation: Position of the camera
  # - cam: bpy camera object
  def update(self,focusPoint,camLocation,cam):
     r=0
     for i in range(2):
         aux=focusPoint[i+1]-camLocation[i+1]
         r=r+aux*aux
     self.radius=math.sqrt(r)
     x=camLocation[2]-focusPoint[2]
     y=camLocation[1]-focusPoint[1]
     z=camLocation[0]-focusPoint[0]
     self.yaw=math.atan2(y,x)
     self.height=z
     self.pitch=math.atan2(self.height,self.radius)
     cam.location=(self.height,self.radius*math.sin(self.yaw),self.radius*math.cos(self.yaw))
     cam.rotation_euler=(self.pitch,self.yaw,self.roll)
     return cam

## Keeps track and renames the current number of objects according to their type and 
# the order in wich they are imported.
# Note 1: When a mesh is imported into blender it comes with default lights and camera
class objectList():
  def __init__(self):
    self.N_Object=0 # Total number of objects
    self.N_Camera=0 # Toral number of cameras
    self.N_Lamp=0  # Total number of lamps
    self.N_Mesh=0 # Total number of meshes
  # Renames the objects according to their type and the order in which they are imported
  # such that their name is Type.order
  def rename(self,item):
    self.N_Object=self.N_Object+1
    print(("Object %s") % self.N_Object)
    print(("Type: %s") % item.type)
    if item.type=='MESH':
      self.N_Mesh=self.N_Mesh+1
      oldDefName=item.name
      print(("Previous default name: %s") % item.name)
      newDefName="Mesh%s" % self.N_Mesh
      bpy.data.objects[oldDefName].name = newDefName
      print(("Current default name: %s") % item.name)
    elif item.type=='CAMERA':
      self.N_Camera=self.N_Camera+1
      oldDefName=item.name
      print(("Previous default name: %s") % item.name)
      newDefName="Camera%s" % self.N_Camera
      bpy.data.objects[oldDefName].name = newDefName
      print(("Current default name: %s") % item.name)
    elif item.type=='LAMP':
      self.N_Lamp=self.N_Lamp+1
      oldDefName=item.name
      print(("Previous default name: %s") % item.name)
      newDefName="Lamp%s" % self.N_Lamp
      bpy.data.objects[oldDefName].name = newDefName
      print(("Current default name: %s") % item.name)
    else:
      print(("WARNING - Unrecognized item type: %s") % item.name)
      print('\n')
    return item



# Deleteing all objects
# Note 1: Sometimes blender is initialized with default objects: cube, light and camera
print('Deleting the following default objects:')
for item in bpy.data.objects:
    print(item.type)
    bpy.data.objects[item.name].select = True
    bpy.ops.object.delete()

# Defining the background color
# Currently light grey
w=bpy.data.worlds['World']
w.horizon_color = (0.8, 0.8, 0.8)
# Should transition color from horizon to zenith but is not working
#w.use_sky_blend=True
#w.zenith_color = (1.0, 0.0, 1.0)



for num in range(start_frame,end_frame+1):
    #######################################################
    # Loading objects and assigning default names to them #
    #######################################################
    # Loading shell: Boundary of the domain in the simulation
    file="/home/ubuntu/alvaro/x3dFiles/domain.x3d"
    print('Render %s' % file)
    bpy.ops.import_scene.x3d(filepath=file, axis_forward='X', axis_up='Z')
    # Loading isoVolume: Volume of a paraview exported property.
             # Example 1: Water volume in a water-air multiphase flow
             # Example 2: 3D Streamlines
    file="/home/ubuntu/alvaro/x3dFiles/t%s.x3d" %(num)
    print('Render %s' % file)
    bpy.ops.import_scene.x3d(filepath=file, axis_forward='X', axis_up='Z')
    # Renaming imported items
    bpy.ops.object.select_all(action='TOGGLE')
    print('\n')
    print('Imported items:\n')
    OL=objectList()
    # Items are renamed depending on the order in which they are imported
    # See objectList.rename for more info.
    for item in bpy.data.objects:
      item=objectList.rename(OL,item)

    ####################################################
    # Renaming objects and assigning materials to them #
    ####################################################
    # Rename first imported mesh object to shell and create a glass-like material for it
    bpy.data.objects["Mesh1"].name = 'shell'
    bpy.data.objects['shell'].select = True
    bpy.ops.object.shade_smooth()
    shell=bpy.data.objects['shell']
    shell=assignGlassMaterial(shell)
    # Rename second imported mesh object to mainObject and create a water-like material for it
    bpy.data.objects["Mesh2"].name = 'mainObject'
    bpy.data.objects['mainObject'].select = True
    bpy.ops.object.shade_smooth()
    ob=bpy.data.objects['mainObject']
    ob=assignWaterMaterial(ob)
    

    # MAKE SOLID MATERIALS
    ob = assignColorMaterial((0,0,1), (0.5,0.5,0), 0.5, ob)
    

    ############################
    # Setting camera position  #
    ############################
    # The camera position is set in two setps:
    # Step 1: Use camera options "camOptions()" to decide the location of the focus point and the camera
    # Step 2: Use "camPosition()" to move the camera to the desired location and make it look towards the focus point
    # We will use the first imported camera
    # Note 1: The initial position of the camera is irrelevant 
    cam = bpy.data.objects["Camera1"]
    # Initializing cam options
    camOp=camOptions()
    # Reading input from json file
    for line in camOpInput:
      camOp.__dict__= json.loads(line)
    # Seting desired camera and focus positions
    focusOb=bpy.data.objects[camOp.focus]
    camOp.setLocations(focusOb) # uses input to calculate both positions
    # Camera will look at focusPoint from camLocation
    focusPoint=camOp.focusPoint
    camLocation=camOp.camLocation
    camPos=camPosition()
    cam=camPos.update(focusPoint,camLocation,cam)
    
    ###################
    # Rendering Scene #
    ###################
    bpy.context.scene.camera = cam
    bpy.context.scene.cycles.samples = 100
    bpy.data.scenes['Scene'].render.filepath = '/home/ubuntu/alvaro/blendedFiles/blended_%d.png' % num
    bpy.ops.render.render(write_still = True)
    
    bpy.ops.object.select_all()
    bpy.ops.object.select_all()
    bpy.ops.object.delete()
