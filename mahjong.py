import bpy
import numpy as np
from PIL import Image
import os
import time

def create_mahjong_tile_from_image(
    image_path,
    tile_size=(2.1, 2.8, 1.2),
    inset_depth=0.1,
    threshold=128,
    pattern_scale=1,  # 新增：图案缩放比例(0-1)
    position=(0, 0, 0),
    name="MahjongTile"
):
    start_time = time.time()

    # 清除场景
    bpy.ops.object.select_all(action='DESELECT')
    bpy.ops.object.select_by_type(type='MESH')
    bpy.ops.object.delete()

    # 创建麻将牌主体
    bpy.ops.mesh.primitive_cube_add(size=1)
    tile = bpy.context.active_object
    tile.name = name
    tile.dimensions = tile_size
    tile.location = position

    try:
        # 加载并预处理图像
        img = Image.open(image_path).convert("RGBA")
        width, height = img.size

        # 计算居中偏移和缩放
        pattern_width = tile_size[0] * pattern_scale
        pattern_height = tile_size[1] * pattern_scale
        
        # 居中偏移量
        offset_x = (tile_size[0] - pattern_width) / 2
        offset_y = (tile_size[1] - pattern_height) / 2

#        # 自动降采样（保留更多细节）
#        if max(width, height) > max_resolution:
#            scale = max_resolution / max(width, height)
#            new_size = (int(width * scale), int(height * scale))
#            img = img.resize(new_size, Image.LANCZOS)  # 高质量插值
#            width, height = new_size
#            print(f"图像降采样至 {width}×{height}（max_resolution={max_resolution}）")
            
        # 二值化处理
        if img.mode == 'RGBA':
            r, g, b, a = img.split()
            a_array = np.array(a)
            # 仅保留 alpha > 0 的区域，且亮度 < threshold
            mask = (a_array > 0) & (np.array(img.convert('L')) < threshold)
            pixels = np.where(mask, 0, 255).astype(np.uint8)
        else:
            # 非 RGBA 图像，原逻辑
            pixels = np.array(img.convert('L'))
            pixels = np.where(pixels < threshold, 0, 255).astype(np.uint8)

        # 创建曲线对象
        curve_data = bpy.data.curves.new(name=f"{name}_Curve", type='CURVE')
        curve_data.dimensions = '3D'
        curve_obj = bpy.data.objects.new(f"{name}_Curve", curve_data)
        bpy.context.collection.objects.link(curve_obj)

        # 曲线参数
        curve_data.resolution_u = 4
        curve_data.fill_mode = 'FULL'
        curve_data.bevel_depth = 0.01

        # 逐像素生成曲线（带缩放和居中）
        for y in range(height):
            for x in range(width):
                if pixels[y, x] < threshold:
                    polyline = curve_data.splines.new('POLY')
                    polyline.points.add(1)

                    # 计算3D位置（带缩放和居中偏移）
                    x_pos = position[0] - tile_size[0]/2 + offset_x + (x/width) * pattern_width
                    y_pos = position[1] - tile_size[1]/2 + offset_y + (y/height) * pattern_height
                    z_pos = position[2] - tile_size[2]/2 + 0.005

                    polyline.points[0].co = (x_pos, y_pos, z_pos, 1)
                    polyline.points[1].co = (x_pos + (1/width)*pattern_width, y_pos, z_pos, 1)

        # 转换为网格
        bpy.context.view_layer.objects.active = curve_obj
        bpy.ops.object.convert(target='MESH')
        cutter = bpy.context.active_object
        cutter.name = f"{name}_Cutter"

        # 进入编辑模式并全选
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')

        # 挤出图案形成凸体（阳文物体），用于布尔差集生成阴文
        bpy.ops.mesh.extrude_region_move(
            TRANSFORM_OT_translate={"value": (0, 0, -inset_depth)}
        )
        bpy.ops.object.mode_set(mode='OBJECT')
        
        # 布尔运算（差集）
        boolean_mod = tile.modifiers.new(name="Boolean", type='DIFFERENCE')
        boolean_mod.operation = 'DIFFERENCE'
        boolean_mod.object = cutter
        bpy.context.view_layer.objects.active = tile
        bpy.ops.object.modifier_apply(modifier=boolean_mod.name)

        # 细分表面
        subdiv_mod = tile.modifiers.new(name="Subdivision", type='SUBSURF')
        subdiv_mod.levels = 2
        subdiv_mod.render_levels = 2
        bpy.ops.object.modifier_apply(modifier=subdiv_mod.name)

        # 清理切割器
        bpy.ops.object.select_all(action='DESELECT')
        cutter.select_set(True)
        bpy.ops.object.delete()

        # 平滑着色 + 材质
        tile.select_set(True)
        bpy.ops.object.shade_smooth()

        # 添加材质
        material = bpy.data.materials.new(name="MahjongMaterial")
        material.use_nodes = True
        bsdf = material.node_tree.nodes["Principled BSDF"]
        bsdf.inputs["Base Color"].default_value = (0.9, 0.9, 0.8, 1.0)
        tile.data.materials.append(material)

        # 输出耗时
        elapsed_time = time.time() - start_time
        print(f"生成完成！耗时: {elapsed_time:.2f}秒 | 面数: {len(tile.data.polygons)}")
        return tile

    except Exception as e:
        print(f"错误: {str(e)}")
        return None

# 使用示例
image_path = "C:\\Users\\HP\\Desktop\\Something\\mahjong\\image\\m1.png"
if os.path.exists(image_path):
    create_mahjong_tile_from_image(
        image_path=image_path,
        pattern_scale=0.9,  # 调整此值控制图案大小
        threshold=100       # 根据图像调整阈值
    )
else:
    print("图片路径无效！")