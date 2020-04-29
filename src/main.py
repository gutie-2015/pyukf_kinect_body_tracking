import sys
sys.path.append('./code/')

from skeleton import Skeleton
from read_data import *
from calibration import Calibration
from IJU_filter import IJU_Filter_Controler
from MJU_filter import MJU_Filter_Controler
from canvas import Canvas
from regression import *

import time
from functools import wraps

def check_time(function):
	@wraps(function)
	def measure(*args, **kwargs):
		start_time = time.time()
		result = function(*args, **kwargs)
		end_time = time.time()
		print(f"@check_time: {function.__name__} took {end_time - start_time}")
		return result

	return measure

def interval_compasation(data, test_num, num):
	if num <= 0:
		return data

	test_num = min(len(data)-1, test_num)
	new_data = []
	for i in range(test_num):
		step_x = []
		step_y = []
		step_z = []
		for j in range(len(data[i])):
			step_x = step_x + [(float(data[i+1][j][0]) - float(data[i][j][0]))/(float)(num)]
			step_y = step_y + [(float(data[i+1][j][1]) - float(data[i][j][1]))/(float)(num)]
			step_z = step_z + [(float(data[i+1][j][2]) - float(data[i][j][2]))/(float)(num)]
		for j in range(num):
			for k in range(len(data[i])):
				new_data = new_data + [float(data[i][k][0]) + step_x[k] * j]
				new_data = new_data + [float(data[i][k][1]) + step_y[k] * j]
				new_data = new_data + [float(data[i][k][2]) + step_z[k] * j]
				new_data = new_data + [float(data[i][k][3])]
				new_data = new_data + [float(data[i][k][4])]
				new_data = new_data + [float(data[i][k][5])]
				new_data = new_data + [float(data[i][k][6])]
	return (int)(len(new_data)/26/7), np.array(new_data).reshape((int)(len(new_data)/26/7),26,7)





def init_simul(filename, test_num, cbr_num=50):
	data = read_data_skeleton(filename)
	test_num, data = interval_compasation(data, test_num, 10)
	skeletons = []
	for d in data:
		skeletons.append(Skeleton(d))

	calibration = Calibration(skeletons[0:cbr_num+1])
	init_mean = calibration.get_init_mean(0, filename)

	return skeletons, init_mean, test_num

def make_filter(init_mean, model, init_cov):
	ukf = None
	if model == 'IJU':
		ukf = IJU_Filter_Controler(init_mean, init_cov)
	elif model == 'MJU':
		ukf = MJU_Filter_Controler(init_mean, init_cov)
	else:
		print(model, "is not exist model name")
	return ukf

def run_ukf(ukf, skeletons, test_num):
	mse_ground_data = []
	mse_estimate_data = []
	draw_ground_data = []
	draw_estimate_data = []

	test_num = min(len(skeletons), test_num)
	for i in range(test_num):
		ret = ukf.update(skeletons[i].get_measurement())
		mse_ground_data = np.append(mse_ground_data, skeletons[i].get_lower_measurement()).reshape(-1)
		mse_estimate_data = np.append(mse_estimate_data, np.array(ret).reshape(-1))

		draw_ground_data.append(skeletons[i].get_measurement())
		draw_estimate_data.append(ret)

	return mse_ground_data, mse_estimate_data, draw_ground_data, draw_estimate_data

def skeleton_draw(ground_data, estimate_data, plot_mode='3D', Ipython=False, test_num=1e9, sleep_t=1):
	canvas = Canvas()
	if plot_mode == '3D':
		canvas.skeleton_3D_plot(ground_data, estimate_data, Ipython, test_num, sleep_t)
	elif plot_mode == 'point':
		canvas.skeleton_point_plot(ground_data, estimate_data, test_num)

@check_time
def simulation_ukf(filename, test_num, model, cbr_num=50):
	skeletons, init_mean, test_num = init_simul(filename, test_num, cbr_num)

	init_cov = [1e-6, 1e-4, 1e-6, 1e-4, 1e-6, 1e-1, 1e-6, 1e-1, 1e-6, 1e-4, 1e-3, 300]
	ukf = make_filter(init_mean, model, init_cov)
	mse_ground_data, mse_estimate_data, draw_ground_data, draw_estimate_data = run_ukf(ukf, skeletons, test_num)
	mse_ret = mean_squared_error(mse_ground_data, mse_estimate_data, test_num)
	print("mean square error: ", mse_ret)
	
	return draw_ground_data, draw_estimate_data

@check_time
def simulation_ukf_brute_force(filename, test_num, model, cbr_num=50):
	skeletons, init_mean, test_num = init_simul(filename, test_num, cbr_num)

	mse_min = 1e9
	mes_min_cov = []
	mes_min_v = []
	mes_min_ground = []
	mes_min_estimate = []

# set covariance
	pos_cov_list = [1e-8, 1e-6, 5]
	velo_cov_list = [1e-9, 1e-8, 3]
	velo_cov_2_list = [1e-9, 2e-8, 3]
	for pos_cov in np.linspace(pos_cov_list[0], pos_cov_list[1], num=pos_cov_list[2]):
		for velo_cov_1 in np.linspace(velo_cov_list[0], velo_cov_list[1], num=velo_cov_list[2]):
			for velo_cov_2 in np.linspace(velo_cov_2_list[0], velo_cov_2_list[1], num=velo_cov_2_list[2]):
				init_cov = [pos_cov, velo_cov_1, pos_cov, velo_cov_1, pos_cov, velo_cov_2, pos_cov, velo_cov_2, pos_cov, velo_cov_1, 1e-4, 100]
				init_min_v = [pos_cov, velo_cov_1, velo_cov_2]
				ukf = make_filter(init_mean, model, init_cov)
				mse_ground_data, mse_estimate_data, draw_ground_data, draw_estimate_data = run_ukf(ukf, skeletons, test_num)
				mse_ret = mean_squared_error(mse_ground_data, mse_estimate_data, test_num) 
				if mse_ret < mse_min:
					mse_min = mse_ret
					mes_min_v = init_min_v
					mes_min_ground = draw_ground_data
					mes_min_estimate = draw_estimate_data
		print(pos_cov, mes_min_v)
	print(mes_min_v)

	return mes_min_ground, mes_min_estimate

if __name__ == "__main__":
	ground_data, estimate_data = simulation_ukf('../data/input_stand.txt', 50, 'IJU', 50)
	if isplot:
		skeleton_draw(ground_data, estimate_data)
