--[[
 Test harness for fuses. Run with the following command:

 dofile("C:\\Users\\rolan\\Dev\\video_production_scripts\\davinci\\test_harness.lua")

]]


-- Dummy function
function FuRegisterClass(arg1, arg2, arg3)
end

dofile("C:\\Users\\rolan\\Dev\\video_production_scripts\\davinci\\bounce_modifier.fuse")

for frame_num = 0.0, 100.0, 0.2
do
	data = bounce_get_height_at_t(20, 10.0, nil, 0.6, 10.0, 25, 0, 1.0, 0.0, false, 8.0, 0.3, frame_num)
	print(frame_num, ",", data[1], ",", data[2], ",", data[3])
end

--[[
curve = bounce_build_animation_curve(20, 10.0, 0.6, 25, 2.0)

for k,v in pairs(curve) do
	print(k,v)
end

]]