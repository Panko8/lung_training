conda activate gdcm

#python train3D.py --exp_name train_rc_2_f0 --crx_valid 0
#python train3D.py --exp_name train_rc_2_f1 --crx_valid 1
#python train3D.py --exp_name train_rc_2_f2 --crx_valid 2
#python train3D.py --exp_name train_rc_2_f3 --crx_valid 3
#python train3D.py --exp_name train_rc_2_f4 --crx_valid 4

python train3D.py --exp_name train_rc_config_4_fp_pool_f0 --crx_valid 0
python train3D.py --exp_name train_rc_config_4_fp_pool_f1 --crx_valid 1
python train3D.py --exp_name train_rc_config_4_fp_pool_f2 --crx_valid 2
python train3D.py --exp_name train_rc_config_4_fp_pool_f3 --crx_valid 3
python train3D.py --exp_name train_rc_config_4_fp_pool_f4 --crx_valid 4