################################################################################
# MRS Version: 2.4.0
# Automatically-generated file. Do not edit!
################################################################################

# Add inputs and outputs from these tool invocations to the build variables 
CC_SRCS += \
../User/tflm/tensorflow/lite/micro/debug_log.cc \
../User/tflm/tensorflow/lite/micro/fake_micro_context.cc \
../User/tflm/tensorflow/lite/micro/flatbuffer_utils.cc \
../User/tflm/tensorflow/lite/micro/hexdump.cc \
../User/tflm/tensorflow/lite/micro/memory_helpers.cc \
../User/tflm/tensorflow/lite/micro/micro_allocation_info.cc \
../User/tflm/tensorflow/lite/micro/micro_allocator.cc \
../User/tflm/tensorflow/lite/micro/micro_context.cc \
../User/tflm/tensorflow/lite/micro/micro_interpreter.cc \
../User/tflm/tensorflow/lite/micro/micro_interpreter_context.cc \
../User/tflm/tensorflow/lite/micro/micro_interpreter_graph.cc \
../User/tflm/tensorflow/lite/micro/micro_log.cc \
../User/tflm/tensorflow/lite/micro/micro_op_resolver.cc \
../User/tflm/tensorflow/lite/micro/micro_profiler.cc \
../User/tflm/tensorflow/lite/micro/micro_resource_variable.cc \
../User/tflm/tensorflow/lite/micro/micro_time.cc \
../User/tflm/tensorflow/lite/micro/micro_utils.cc \
../User/tflm/tensorflow/lite/micro/mock_micro_graph.cc \
../User/tflm/tensorflow/lite/micro/recording_micro_allocator.cc \
../User/tflm/tensorflow/lite/micro/system_setup.cc \
../User/tflm/tensorflow/lite/micro/test_helper_custom_ops.cc \
../User/tflm/tensorflow/lite/micro/test_helpers.cc 

CC_DEPS += \
./User/tflm/tensorflow/lite/micro/debug_log.d \
./User/tflm/tensorflow/lite/micro/fake_micro_context.d \
./User/tflm/tensorflow/lite/micro/flatbuffer_utils.d \
./User/tflm/tensorflow/lite/micro/hexdump.d \
./User/tflm/tensorflow/lite/micro/memory_helpers.d \
./User/tflm/tensorflow/lite/micro/micro_allocation_info.d \
./User/tflm/tensorflow/lite/micro/micro_allocator.d \
./User/tflm/tensorflow/lite/micro/micro_context.d \
./User/tflm/tensorflow/lite/micro/micro_interpreter.d \
./User/tflm/tensorflow/lite/micro/micro_interpreter_context.d \
./User/tflm/tensorflow/lite/micro/micro_interpreter_graph.d \
./User/tflm/tensorflow/lite/micro/micro_log.d \
./User/tflm/tensorflow/lite/micro/micro_op_resolver.d \
./User/tflm/tensorflow/lite/micro/micro_profiler.d \
./User/tflm/tensorflow/lite/micro/micro_resource_variable.d \
./User/tflm/tensorflow/lite/micro/micro_time.d \
./User/tflm/tensorflow/lite/micro/micro_utils.d \
./User/tflm/tensorflow/lite/micro/mock_micro_graph.d \
./User/tflm/tensorflow/lite/micro/recording_micro_allocator.d \
./User/tflm/tensorflow/lite/micro/system_setup.d \
./User/tflm/tensorflow/lite/micro/test_helper_custom_ops.d \
./User/tflm/tensorflow/lite/micro/test_helpers.d 

OBJS += \
./User/tflm/tensorflow/lite/micro/debug_log.o \
./User/tflm/tensorflow/lite/micro/fake_micro_context.o \
./User/tflm/tensorflow/lite/micro/flatbuffer_utils.o \
./User/tflm/tensorflow/lite/micro/hexdump.o \
./User/tflm/tensorflow/lite/micro/memory_helpers.o \
./User/tflm/tensorflow/lite/micro/micro_allocation_info.o \
./User/tflm/tensorflow/lite/micro/micro_allocator.o \
./User/tflm/tensorflow/lite/micro/micro_context.o \
./User/tflm/tensorflow/lite/micro/micro_interpreter.o \
./User/tflm/tensorflow/lite/micro/micro_interpreter_context.o \
./User/tflm/tensorflow/lite/micro/micro_interpreter_graph.o \
./User/tflm/tensorflow/lite/micro/micro_log.o \
./User/tflm/tensorflow/lite/micro/micro_op_resolver.o \
./User/tflm/tensorflow/lite/micro/micro_profiler.o \
./User/tflm/tensorflow/lite/micro/micro_resource_variable.o \
./User/tflm/tensorflow/lite/micro/micro_time.o \
./User/tflm/tensorflow/lite/micro/micro_utils.o \
./User/tflm/tensorflow/lite/micro/mock_micro_graph.o \
./User/tflm/tensorflow/lite/micro/recording_micro_allocator.o \
./User/tflm/tensorflow/lite/micro/system_setup.o \
./User/tflm/tensorflow/lite/micro/test_helper_custom_ops.o \
./User/tflm/tensorflow/lite/micro/test_helpers.o 

DIR_OBJS += \
./User/tflm/tensorflow/lite/micro/*.o \

DIR_DEPS += \
./User/tflm/tensorflow/lite/micro/*.d \

DIR_EXPANDS += \
./User/tflm/tensorflow/lite/micro/*.253r.expand \


# Each subdirectory must supply rules for building sources it contributes
User/tflm/tensorflow/lite/micro/%.o: ../User/tflm/tensorflow/lite/micro/%.cc
	@	riscv-wch-elf-g++ -march=rv32imac_zba_zbb_zbc_zbs_xw -mabi=ilp32 -msmall-data-limit=8 -msave-restore -fmax-errors=20 -Os -fmessage-length=0 -fsigned-char -ffunction-sections -fdata-sections -fno-common -Wunused -Wuninitialized -g -I"c:/Users/13228/Desktop/Match/CH32H417/TFLM_EyeTracking/V5F/User/tflm" -I"c:/Users/13228/Desktop/Match/CH32H417/TFLM_EyeTracking/V5F/User/tflm/third_party/kissfft" -I"c:/Users/13228/Desktop/Match/CH32H417/TFLM_EyeTracking/V5F/User/tflm/third_party/flatbuffers/include" -I"c:/Users/13228/Desktop/Match/CH32H417/TFLM_EyeTracking/V5F/User/tflm/third_party/gemmlowp" -I"c:/Users/13228/Desktop/Match/CH32H417/TFLM_EyeTracking/V5F/User/tflm/third_party/ruy" -I"c:/Users/13228/Desktop/Match/CH32H417/sdk_ch32h417/SRC/Debug" -I"c:/Users/13228/Desktop/Match/CH32H417/sdk_ch32h417/SRC/Core" -I"c:/Users/13228/Desktop/Match/CH32H417/TFLM_EyeTracking/V5F/User" -I"c:/Users/13228/Desktop/Match/CH32H417/sdk_ch32h417/SRC/Peripheral/inc" -std=gnu++11 -fabi-version=0 -MMD -MP -MF"$(@:%.o=%.d)" -MT"$(@)" -c -o "$@" "$<"

