################################################################################
# MRS Version: 2.4.0
# Automatically-generated file. Do not edit!
################################################################################
-include ../makefile.init

RM := rm -rf

# All of the sources participating in the build are defined here
-include sources.mk
-include User/subdir.mk
-include Startup/subdir.mk
-include Peripheral/src/subdir.mk
-include Debug/subdir.mk
-include Core/subdir.mk
-include Common/subdir.mk
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
endif

-include ../makefile.defs

# Add inputs and outputs from these tool invocations to the build variables 
SECONDARY_FLASH += \
DVP_UART_V3F.bin \
DVP_UART_V3F.hex \

SECONDARY_LIST += \
DVP_UART_V3F.lst \

SECONDARY_SIZE += \
DVP_UART_V3F.siz \


# All Target
all: 
	$(MAKE) --no-print-directory main-build 

main-build: DVP_UART_V3F.elf secondary-outputs

# Tool invocations
DVP_UART_V3F.elf: $(OBJS) $(USER_OBJS_ESCAPE)
	@	riscv-wch-elf-gcc -march=rv32imac_zba_zbb_zbc_zbs_xw -mabi=ilp32 -msmall-data-limit=8 -msave-restore -fmax-errors=20 -Os -fmessage-length=0 -fsigned-char -ffunction-sections -fdata-sections -fno-common -Wunused -Wuninitialized -g -T "e:\dvp-uart\Match\CH32H417\sdk_ch32h417\SRC\Ld\V3F\Link_v3f.ld" -nostartfiles -Xlinker --gc-sections -Wl,-Map,"DVP_UART_V3F.map" --specs=nano.specs --specs=nosys.specs -o "DVP_UART_V3F.elf" $(OBJS) $(LIBS)
DVP_UART_V3F.bin: DVP_UART_V3F.elf
	@	riscv-wch-elf-objcopy -O binary "DVP_UART_V3F.elf" "DVP_UART_V3F.bin"
DVP_UART_V3F.hex: DVP_UART_V3F.elf
	@	riscv-wch-elf-objcopy -O ihex "DVP_UART_V3F.elf" "DVP_UART_V3F.hex"
DVP_UART_V3F.lst: DVP_UART_V3F.elf
	@	riscv-wch-elf-objdump --all-headers --demangle --disassemble -M xw "DVP_UART_V3F.elf" > "DVP_UART_V3F.lst"
DVP_UART_V3F.siz: DVP_UART_V3F.elf
	riscv-wch-elf-size --format=berkeley "DVP_UART_V3F.elf"

# Other Targets
clean:
	-$(RM) $(DIR_OBJS) $(SECONDARY_FLASH)$(SECONDARY_LIST)$(SECONDARY_SIZE) DVP_UART_V3F.elf
	-$(RM) $(DIR_EXPANDS) $(CALLGRAPH_DOT)
	-$(RM) $(DIR_DEPS)
secondary-outputs: $(SECONDARY_FLASH) $(SECONDARY_LIST) $(SECONDARY_SIZE)

.PHONY: all clean dependents

-include ../makefile.targets