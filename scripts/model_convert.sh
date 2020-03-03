#!/bin/bash

PATH_TO_MODEL_DIR=$1
export CONFIG_FILE=$PATH_TO_MODEL_DIR/pipeline.config
export CHECKPOINT_PATH=$PATH_TO_MODEL_DIR/model.ckpt
export OUTPUT_DIR=$PATH_TO_MODEL_DIR/tflite

cd ~/models/research
export PYTHONPATH=$PYTHONPATH:`pwd`:`pwd`/slim
python3 object_detection/export_tflite_ssd_graph.py --pipeline_config_path=$CONFIG_FILE --trained_checkpoint_prefix=$CHECKPOINT_PATH --output_directory=$OUTPUT_DIR --add_postprocessing_op=true

cd $PATH_TO_MODEL_DIR/tflite
#Quantized CHANGE INPUT_SHAPES BY MODEL
tflite_convert --input_arrays normalized_input_image_tensor --input_shapes 1,320,320,3  --graph_def_file ./tflite_graph.pb --output_file=model_quantized.tflite --output_arrays='TFLite_Detection_PostProcess','TFLite_Detection_PostProcess:1','TFLite_Detection_PostProcess:2','TFLite_Detection_PostProcess:3' --output_format TFLITE --inference_input_type QUANTIZED_UINT8 --allow_custom_ops --change_concat_input_ranges TRUE --input_format=TENSORFLOW_GRAPHDEF --output_format=TFLITE --std_dev_values 128 --mean_values 128

#Float CHANGE INPUT_SHAPES BY MODEL
tflite_convert --input_arrays normalized_input_image_tensor --input_shapes 1,320,320,3  --graph_def_file ./tflite_graph.pb --output_file=model_float.tflite --output_arrays='TFLite_Detection_PostProcess','TFLite_Detection_PostProcess:1','TFLite_Detection_PostProcess:2','TFLite_Detection_PostProcess:3' --output_format TFLITE --inference_input_type FLOAT --allow_custom_ops --change_concat_input_ranges TRUE --input_format=TENSORFLOW_GRAPHDEF --output_format=TFLITE
