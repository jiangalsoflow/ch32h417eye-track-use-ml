################################################################################
# MRS Version: 2.4.0
# Automatically-generated file. Do not edit!
################################################################################
-include ../makefile.init

RM := rm -rf

# All of the sources participating in the build are defined here
-include sources.mk
-include User/tflm/third_party/kissfft/tools/subdir.mk
-include User/tflm/third_party/kissfft/subdir.mk
-include User/tflm/tensorflow/lite/micro/tflite_bridge/subdir.mk
-include User/tflm/tensorflow/lite/micro/memory_planner/subdir.mk
-include User/tflm/tensorflow/lite/micro/kernels/subdir.mk
-include User/tflm/tensorflow/lite/micro/examples/person_detection/subdir.mk
-include User/tflm/tensorflow/lite/micro/examples/hello_world/models/subdir.mk
-include User/tflm/tensorflow/lite/micro/arena_allocator/subdir.mk
-include User/tflm/tensorflow/lite/micro/subdir.mk
-include User/tflm/tensorflow/lite/kernels/internal/reference/subdir.mk
-include User/tflm/tensorflow/lite/kernels/internal/subdir.mk
-include User/tflm/tensorflow/lite/kernels/subdir.mk
-include User/tflm/tensorflow/lite/core/c/subdir.mk
-include User/tflm/tensorflow/lite/core/api/subdir.mk
-include User/tflm/tensorflow/compiler/mlir/lite/schema/subdir.mk
-include User/tflm/tensorflow/compiler/mlir/lite/core/api/subdir.mk
-include User/tflm/signal/src/kiss_fft_wrappers/subdir.mk
-include User/tflm/signal/src/subdir.mk
-include User/tflm/signal/micro/kernels/subdir.mk
-include User/tflm/subdir.mk
-include User/subdir.mk
-include Startup/subdir.mk
-include Peripheral/src/subdir.mk
-include Debug/subdir.mk
-include Core/subdir.mk
-include subdir.mk
-include objects.mk

ifneq ($(MAKECMDGOALS),clean)
ifneq ($(strip $(S_DEPS)),)
-include $(S_DEPS)
endif
ifneq ($(strip $(S_UPPER_DEPS)),)
-include $(S_UPPER_DEPS)
endif
ifneq ($(strip $(ASM_DEPS)),)
-include $(ASM_DEPS)
endif
ifneq ($(strip $(ASM_UPPER_DEPS)),)
-include $(ASM_UPPER_DEPS)
endif
ifneq ($(strip $(C_DEPS)),)
-include $(C_DEPS)
endif
ifneq ($(strip $(C_UPPER_DEPS)),)
-include $(C_UPPER_DEPS)
endif
ifneq ($(strip $(CC_DEPS)),)
-include $(CC_DEPS)
endif
ifneq ($(strip $(C++_DEPS)),)
-include $(C++_DEPS)
endif
ifneq ($(strip $(CXX_DEPS)),)
-include $(CXX_DEPS)
endif
ifneq ($(strip $(CPP_DEPS)),)
-include $(CPP_DEPS)
endif
endif

-include ../makefile.defs

# Add inputs and outputs from these tool invocations to the build variables 
SECONDARY_FLASH += \
TFLM_EyeTrack_V5F.bin \
TFLM_EyeTrack_V5F.hex \

SECONDARY_LIST += \
TFLM_EyeTrack_V5F.lst \

SECONDARY_SIZE += \
TFLM_EyeTrack_V5F.siz \


# All Target
all: 
	$(MAKE) --no-print-directory main-build 

main-build: TFLM_EyeTrack_V5F.elf secondary-outputs

# Tool invocations
TFLM_EyeTrack_V5F.elf: $(OBJS) $(USER_OBJS_ESCAPE)
	@	riscv-wch-elf-g++ -march=rv32imac_zba_zbb_zbc_zbs_xw -mabi=ilp32 -msmall-data-limit=8 -msave-restore -fmax-errors=20 -Os -fmessage-length=0 -fsigned-char -ffunction-sections -fdata-sections -fno-common -Wunused -Wuninitialized -g -T "c:\Users\13228\Desktop\Match\CH32H417\sdk_ch32h417\SRC\Ld\V5F\Link_v5f.ld" -nostartfiles -Xlinker --gc-sections -Wl,-Map,"TFLM_EyeTrack_V5F.map" --specs=nano.specs --specs=nosys.specs -o "TFLM_EyeTrack_V5F.elf" $(OBJS) $(LIBS)
TFLM_EyeTrack_V5F.bin: TFLM_EyeTrack_V5F.elf
	@	riscv-wch-elf-objcopy -O binary "TFLM_EyeTrack_V5F.elf" "TFLM_EyeTrack_V5F.bin"
TFLM_EyeTrack_V5F.hex: TFLM_EyeTrack_V5F.elf
	@	riscv-wch-elf-objcopy -O ihex "TFLM_EyeTrack_V5F.elf" "TFLM_EyeTrack_V5F.hex"
TFLM_EyeTrack_V5F.lst: TFLM_EyeTrack_V5F.elf
	@	riscv-wch-elf-objdump --all-headers --demangle --disassemble -M xw "TFLM_EyeTrack_V5F.elf" > "TFLM_EyeTrack_V5F.lst"
TFLM_EyeTrack_V5F.siz: TFLM_EyeTrack_V5F.elf
	riscv-wch-elf-size --format=berkeley "TFLM_EyeTrack_V5F.elf"

# Other Targets
clean:
	-$(RM) $(DIR_OBJS) $(SECONDARY_FLASH)$(SECONDARY_LIST)$(SECONDARY_SIZE) TFLM_EyeTrack_V5F.elf
	-$(RM) $(DIR_EXPANDS) $(CALLGRAPH_DOT)
	-$(RM) $(DIR_DEPS)
secondary-outputs: $(SECONDARY_FLASH) $(SECONDARY_LIST) $(SECONDARY_SIZE)

.PHONY: all clean dependents

-include ../makefile.targets