#!/usr/bin/env python3
"""
CS4200 - Semester Project
Pipeline with Hazard Detection
Added Sections:
Hazard detection Class Starts at line 24:
- Tracks total instructions, stall cycles, RAW hazards, load-use hazards
- Methods to record hazards and compute CPI
-Creates the final log file
Enhanced RAW Hazard Detection Function at line 287:
- Checks for RAW hazards against both EX/MEM and MEM/WB stages
- Records detailed hazard info in the log
Enhanced Load-Use Hazard Detection Function at line 328:
- Records load-use hazards in the hazard detector
Changes to main loop:
- Calls hazard detection functions at the start of each cycle
- Updates the hazard detector with instruction counts and stalls
- Writes a comprehensive hazard report at the end of simulation

"""

MASK32 = 0xFFFFFFFF

# ===== HAZARD DETECTION: New data structures for performance tracking =====
class HazardDetector:
    
    #Tracks RAW hazards and performance metrics.
    def __init__(self):
        self.total_instructions = 0
        self.stall_cycles = 0
        self.raw_hazards_detected = 0
        self.load_use_hazards = 0

        # List of (cycle, hazard_type, reg, instr_pc)
        self.hazard_log = []  

    #Record a RAW hazard detection.   
    def record_raw_hazard(self, cycle, reg, instr_pc, hazard_type="RAW"):
        
        self.raw_hazards_detected += 1
        self.hazard_log.append({
            'cycle': cycle,
            'type': hazard_type,
            'register': reg,
            'instr_pc': instr_pc
        })
    
    #Record a load-use stall.
    def record_load_use_hazard(self, cycle):
        self.load_use_hazards += 1
        self.stall_cycles += 1
    
    #Count a non-NOP instruction.
    def record_instruction(self):
        self.total_instructions += 1
    
    #Compute Cycles Per Instruction.
    def compute_cpi(self, total_cycles):
        if self.total_instructions == 0:
            return 0.0
        return total_cycles / self.total_instructions
    
    #Print performance report.
    def write_report(self, total_cycles, filename="hazard_report.log"):
        cpi = self.compute_cpi(total_cycles)
        with open(filename, 'w') as f:
            f.write("\n" + "="*60 + "\n")
            f.write("PIPELINE HAZARD DETECTION & PERFORMANCE REPORT\n")
            f.write("="*60 + "\n")
            f.write(f"Total Instructions Executed:  {self.total_instructions}\n")
            f.write(f"Total Cycles:                 {total_cycles}\n")
            f.write(f"Stall Cycles:                 {self.stall_cycles}\n")
            f.write(f"Pipeline CPI:                 {cpi:.3f}\n")
            f.write(f"Ideal CPI (no hazards):       1.000\n")
            f.write(f"CPI Overhead:                 {cpi - 1.0:.3f}\n")
            f.write(f"\nHazard Statistics:\n")
            f.write(f"  RAW Hazards Detected:       {self.raw_hazards_detected}\n")
            f.write(f"  Load-Use Stalls:            {self.load_use_hazards}\n")
            if self.total_instructions > 0:
                stall_pct = (self.stall_cycles / total_cycles) * 100
                f.write(f"  Stall % of cycles:          {stall_pct:.1f}%\n")
            f.write("="*60 + "\n\n")
            
            if self.hazard_log:
                f.write("Hazard Events (all):\n")
                for i, h in enumerate(self.hazard_log):
                    f.write(f"  Cycle {h['cycle']:3d}: {h['type']:12s} reg x{h['register']:2d} at PC 0x{h['instr_pc']:08x}\n")
 
 
# ===== END HAZARD DETECTION SECTION =====

# ------------------------------------------------------------
# 32-bit helpers
# ------------------------------------------------------------

def u32(x):
   
    return x & MASK32


def s32(x):
   
    x = x & MASK32
    if x & 0x80000000:
        return x - 0x100000000
    return x


def sign_extend(value, bits):
   
    sign_bit = 1 << (bits - 1)
    if value & sign_bit:
        return value - (1 << bits)
    return value


def get_bits(x, hi, lo):
   
    return (x >> lo) & ((1 << (hi - lo + 1)) - 1)


# ------------------------------------------------------------
# Immediate generators
# ------------------------------------------------------------

def imm_i(instr):
   
    imm = get_bits(instr, 31, 20)
    return sign_extend(imm, 12)


def imm_s(instr):
    
    upper = get_bits(instr, 31, 25)
    lower = get_bits(instr, 11, 7)
    imm = (upper << 5) | lower
    return sign_extend(imm, 12)


def imm_b(instr):
    
    bit_12 = get_bits(instr, 31, 31)
    bit_11 = get_bits(instr, 7, 7)
    bits_10_5 = get_bits(instr, 30, 25)
    bits_4_1 = get_bits(instr, 11, 8)
    imm = (bit_12 << 12) | (bit_11 << 11) | (bits_10_5 << 5) | (bits_4_1 << 1)
    return sign_extend(imm, 13)


def imm_u(instr):
   
    return (get_bits(instr, 31, 12) << 12) & MASK32


def imm_j(instr):
   
    bit_20 = get_bits(instr, 31, 31)
    bits_10_1 = get_bits(instr, 30, 21)
    bit_11 = get_bits(instr, 20, 20)
    bits_19_12 = get_bits(instr, 19, 12)
    imm = (bit_20 << 20) | (bit_11 << 11) | (bits_19_12 << 12) | (bits_10_1 << 1)
    return sign_extend(imm, 21)


# ------------------------------------------------------------
# Decode + Control
# ------------------------------------------------------------

def decode(instr):
    """
    TODO: return dict with fields:
      instr, opcode, rd, funct3, rs1, rs2, funct7
      imm_I, imm_S, imm_B, imm_U, imm_J
    """
    d = {}
    d["instr"] = instr
    d["opcode"] = get_bits(instr, 6, 0)
    d["rd"] = get_bits(instr, 11, 7)
    d["funct3"] = get_bits(instr, 14, 12)
    d["rs1"] = get_bits(instr, 19, 15)
    d["rs2"] = get_bits(instr, 24, 20)
    d["funct7"] = get_bits(instr, 31, 25)
    d["imm_I"] = imm_i(instr)
    d["imm_S"] = imm_s(instr)
    d["imm_B"] = imm_b(instr)
    d["imm_U"] = imm_u(instr)
    d["imm_J"] = imm_j(instr)
    return d


def main_control(d):
    
    c = {
        "RegWrite": 0,
        "MemRead": 0,
        "MemWrite": 0,
        "MemToReg": 0,
        "ALUSrc": 0,
        "Branch": 0,
        "Jump": 0,
        "JumpReg": 0,
        "ALUOp": "ADDR",
        "ImmSel": None,
        "BrType": None,
        "IsNOP": 0,
    }
 
    if d["instr"] == 0:
        c["IsNOP"] = 1
        return c
 
    opcode = d["opcode"]
    funct3 = d["funct3"]
 
    # R-type: add, sub, and, or, xor, sll, srl, sra, slt, sltu (opcode=51)
    if opcode == 0b0110011:
        c["RegWrite"] = 1
        c["ALUOp"] = "R"
        return c
 
    # I-type ALU: addi, andi, ori, xori, slti, sltiu, slli, srli, srai (opcode=19)
    if opcode == 0b0010011:
        c["RegWrite"] = 1
        c["ALUSrc"] = 1
        c["ALUOp"] = "I"
        c["ImmSel"] = "I"
        return c
 
    # lw (opcode=3, funct3=010)
    if opcode == 0b0000011 and funct3 == 0b010:
        c["RegWrite"] = 1
        c["MemRead"] = 1
        c["MemToReg"] = 1
        c["ALUSrc"] = 1
        c["ALUOp"] = "ADDR"
        c["ImmSel"] = "I"
        return c
 
    # sw (opcode=35, funct3=010)
    if opcode == 0b0100011 and funct3 == 0b010:
        c["MemWrite"] = 1
        c["ALUSrc"] = 1
        c["ALUOp"] = "ADDR"
        c["ImmSel"] = "S"
        return c
 
    # beq, bne, blt, bge, bltu, bgeu (opcode=99)
    if opcode == 0b1100011:
        c["Branch"] = 1
        c["ALUOp"] = "BR"
        c["ImmSel"] = "B"
        # Map funct3 to branch type
        if funct3 == 0b000:
            c["BrType"] = "beq"
        elif funct3 == 0b001:
            c["BrType"] = "bne"
        elif funct3 == 0b100:
            c["BrType"] = "blt"
        elif funct3 == 0b101:
            c["BrType"] = "bge"
        elif funct3 == 0b110:
            c["BrType"] = "bltu"
        elif funct3 == 0b111:
            c["BrType"] = "bgeu"
        return c
 
    # jal (opcode=111)
    if opcode == 0b1101111:
        c["RegWrite"] = 1
        c["Jump"] = 1
        c["ImmSel"] = "J"
        return c
 
    # jalr (opcode=103, funct3=000)
    if opcode == 0b1100111 and funct3 == 0b000:
        c["RegWrite"] = 1
        c["Jump"] = 1
        c["JumpReg"] = 1
        c["ALUSrc"] = 1
        c["ImmSel"] = "I"
        return c
 
    # Unrecognized -> treat as NOP
    c["IsNOP"] = 1
    return c

# ===== HAZARD DETECTION: Enhanced RAW Hazard Detection Function =====
def detect_raw_hazard(if_id_instr, id_ex, ex_mem, mem_wb, hazard_detector, cycle):
   
    if if_id_instr == 0 or if_id_instr is None:
        return False, -1
    
    d_id = decode(if_id_instr)
    rs1 = d_id.get("rs1", 0)
    rs2 = d_id.get("rs2", 0)
    
    # Check against EX/MEM stage
    if ex_mem.get("valid", 0):
        ex_mem_rd = ex_mem.get("rd", 0)
        ex_mem_c = ex_mem.get("c")
        
        # RAW hazard if EX/MEM writes to a register we're reading
        if ex_mem_c and ex_mem_c.get("RegWrite", 0) and ex_mem_rd != 0:
            if rs1 == ex_mem_rd:
                hazard_detector.record_raw_hazard(cycle, rs1, 
                    if_id_instr, "RAW_from_EXMEM")
                return True, rs1
            if rs2 == ex_mem_rd:
                hazard_detector.record_raw_hazard(cycle, rs2,
                    if_id_instr, "RAW_from_EXMEM")
                return True, rs2
    
    # Check against MEM/WB stage (only if not available from forwarding)
    if mem_wb.get("valid", 0):
        mem_wb_rd = mem_wb.get("rd", 0)
        mem_wb_c = mem_wb.get("c")
        
        # RAW hazard if MEM/WB writes to a register we're reading
        if mem_wb_c and mem_wb_c.get("RegWrite", 0) and mem_wb_rd != 0:
            if rs1 == mem_wb_rd:
                # This would be handled by forwarding in normal case
                pass
            if rs2 == mem_wb_rd:
                pass
    
    return False, -1
 
    #===== ENHANCED FUNCTION: Load-Use Hazard Detection =====
def detect_load_use_hazard_enhanced(if_id, id_ex, hazard_detector, cycle):
    
    if not if_id.get("valid", 0) or not id_ex.get("valid", 0):
        return False
    
    instr_id = if_id.get("instr", 0)
    if instr_id == 0:
        return False
    
    d_id = decode(instr_id)
    rs1 = d_id.get("rs1", 0)
    rs2 = d_id.get("rs2", 0)
    
    # Check if ID/EX is doing a load (lw)
    id_ex_c = id_ex.get("c")
    if not id_ex_c or not id_ex_c.get("MemRead", 0):
        return False
    
    id_ex_rd = id_ex.get("rd", 0)
    
    # If either rs1 or rs2 matches the destination of the load
    if (rs1 != 0 and rs1 == id_ex_rd) or (rs2 != 0 and rs2 == id_ex_rd):
        hazard_detector.record_load_use_hazard(cycle)
        hazard_detector.record_raw_hazard(cycle, id_ex_rd,
            if_id.get("pc", 0), "LOAD_USE")
        return True
    
    return False
 
 
# ===== END HAZARD DETECTION SECTION ====

def select_imm(d, c):
    
    imm_sel = c["ImmSel"]
    if imm_sel == "I":
        return d["imm_I"]
    elif imm_sel == "S":
        return d["imm_S"]
    elif imm_sel == "B":
        return d["imm_B"]
    elif imm_sel == "U":
        return d["imm_U"]
    elif imm_sel == "J":
        return d["imm_J"]
    else:
        return 0


# ------------------------------------------------------------
# ALU control + ALU
# ------------------------------------------------------------

def alu_control(c, d):
    
    alu_op = c["ALUOp"]
 
    if alu_op == "ADDR":
        # For address calculation (lw, sw)
        return "ADD"
 
    if alu_op == "BR":
        # For branches, we'll use ALU for comparison in branch_taken
        # Return ADD as default (not used in ALU, comparison happens elsewhere)
        return "ADD"
 
    funct3 = d["funct3"]
    funct7 = d["funct7"]
 
    if alu_op == "R":
        # R-type: use funct7 and funct3
        if funct3 == 0b000:
            if funct7 == 0b0000000:
                return "ADD"
            elif funct7 == 0b0100000:
                return "SUB"
        elif funct3 == 0b001:
            return "SLL"
        elif funct3 == 0b010:
            return "SLT"
        elif funct3 == 0b011:
            return "SLTU"
        elif funct3 == 0b100:
            return "XOR"
        elif funct3 == 0b101:
            if funct7 == 0b0000000:
                return "SRL"
            elif funct7 == 0b0100000:
                return "SRA"
        elif funct3 == 0b110:
            return "OR"
        elif funct3 == 0b111:
            return "AND"
        return "ADD"
 
    if alu_op == "I":
        # I-type: use funct3 (and funct7 for shift)
        if funct3 == 0b000:
            return "ADD"
        elif funct3 == 0b010:
            return "SLT"
        elif funct3 == 0b011:
            return "SLTU"
        elif funct3 == 0b100:
            return "XOR"
        elif funct3 == 0b110:
            return "OR"
        elif funct3 == 0b111:
            return "AND"
        elif funct3 == 0b001:
            return "SLL"
        elif funct3 == 0b101:
            if funct7 == 0b0000000:
                return "SRL"
            elif funct7 == 0b0100000:
                return "SRA"
        return "ADD"
 
    return "ADD"


def alu_exec(alu_op, a, b):
    
    a = s32(a)
    b = s32(b)
 
    if alu_op == "ADD":
        return u32(a + b)
    elif alu_op == "SUB":
        return u32(a - b)
    elif alu_op == "AND":
        return u32(a & b)
    elif alu_op == "OR":
        return u32(a | b)
    elif alu_op == "XOR":
        return u32(a ^ b)
    elif alu_op == "SLL":
        shamt = u32(b) & 0x1F
        return u32(a << shamt)
    elif alu_op == "SRL":
        shamt = u32(b) & 0x1F
        return u32(u32(a) >> shamt)
    elif alu_op == "SRA":
        shamt = u32(b) & 0x1F
        # Arithmetic right shift (signed)
        result = a >> shamt
        return u32(result)
    elif alu_op == "SLT":
        # Signed compare
        return 1 if a < b else 0
    elif alu_op == "SLTU":
        # Unsigned compare
        ua = u32(a)
        ub = u32(b)
        return 1 if ua < ub else 0
    else:
        return 0


def branch_taken(br_type, rs1_val, rs2_val):
   
    rs1_val = s32(rs1_val)
    rs2_val = s32(rs2_val)
    urs1_val = u32(rs1_val)
    urs2_val = u32(rs2_val)
 
    if br_type == "beq":
        return rs1_val == rs2_val
    elif br_type == "bne":
        return rs1_val != rs2_val
    elif br_type == "blt":
        return rs1_val < rs2_val
    elif br_type == "bge":
        return rs1_val >= rs2_val
    elif br_type == "bltu":
        return urs1_val < urs2_val
    elif br_type == "bgeu":
        return urs1_val >= urs2_val
    else:
        return False


# ------------------------------------------------------------
# Data memory (word aligned)
# ------------------------------------------------------------

def dmem_load_word(dmem, addr):
    
    addr = u32(addr)
    if addr % 4 != 0:
        # Misaligned access - could trap, but allow for now
        pass
    return u32(dmem.get(addr, 0))


def dmem_store_word(dmem, addr, value):
   
    addr = u32(addr)
    if addr % 4 != 0:
        # Misaligned access - could trap, but allow for now
        pass
    dmem[addr] = u32(value)


# ------------------------------------------------------------
# Pipeline registers
# ------------------------------------------------------------

def make_if_id():
    """IF/ID pipeline register bundle."""
    return {"valid": 0, "pc": 0, "instr": 0}


def make_id_ex():
    """ID/EX pipeline register bundle."""
    return {
        "valid": 0,
        "pc": 0,
        "pc_plus4": 0,
        "d": None,
        "c": None,
        "imm": 0,
        "rs1": 0,
        "rs2": 0,
        "rd": 0,
        "rs1_val": 0,
        "rs2_val": 0,
        "alu_op": "ADD",
    }


def make_ex_mem():
    """EX/MEM pipeline register bundle."""
    return {
        "valid": 0,
        "pc_plus4": 0,
        "c": None,
        "d": None,
        "rd": 0,
        "alu_res": 0,
        "rs2_val_fwd": 0,     # store data after forwarding
        "mem_addr": 0,
        "branch_taken": 0,
        "next_pc": 0,
        "wb_val_for_jumps": 0 # pc+4 for jal/jalr
    }


def make_mem_wb():
    """MEM/WB pipeline register bundle."""
    return {
        "valid": 0,
        "pc_plus4": 0,
        "c": None,
        "d": None,
        "rd": 0,
        "alu_res": 0,
        "mem_data": 0,
        "wb_val_for_jumps": 0
    }


# ------------------------------------------------------------
# Hazard detection helpers
# ------------------------------------------------------------

def uses_rs1(d):
   
    if d is None or d["instr"] == 0:
        return False
    
    opcode = d["opcode"]
    
    # jal doesn't use rs1
    if opcode == 0b1101111:
        return False
    
    # Most other instructions use rs1
    return True


def uses_rs2(d):
    
    if d is None or d["instr"] == 0:
        return False
    
    opcode = d["opcode"]
    
    # R-type (opcode=51)
    if opcode == 0b0110011:
        return True
    
    # sw (opcode=35)
    if opcode == 0b0100011:
        return True
    
    # branches (opcode=99)
    if opcode == 0b1100011:
        return True
    
    return False


def is_load_c(c):
    
    if c is None:
        return False
    return c.get("MemRead", 0) == 1 and c.get("MemToReg", 0) == 1
 
def will_write_c(c):
    """Return True if RegWrite==1."""
    if c is None:
        return False
    return c.get("RegWrite", 0) == 1


def forwarding_select(src_reg, ex_mem, mem_wb):
    
    if src_reg == 0:
        return False, 0
 
    # Priority 1: EX/MEM (but NOT if it's a load, since data not ready)
    if ex_mem["valid"]:
        c_ex_mem = ex_mem.get("c")
        if c_ex_mem and will_write_c(c_ex_mem) and not is_load_c(c_ex_mem):
            if ex_mem.get("rd") == src_reg:
                # Check if it's a jump (jal/jalr)
                d_ex_mem = ex_mem.get("d")
                if d_ex_mem:
                    opcode = d_ex_mem.get("opcode", 0)
                    if opcode == 0b1101111 or opcode == 0b1100111:
                        return True, ex_mem.get("wb_val_for_jumps", 0)
                return True, ex_mem.get("alu_res", 0)
 
    # Priority 2: MEM/WB
    if mem_wb["valid"]:
        c_mem_wb = mem_wb.get("c")
        if c_mem_wb and will_write_c(c_mem_wb):
            if mem_wb.get("rd") == src_reg:
                # Check if it's a jump
                d_mem_wb = mem_wb.get("d")
                if d_mem_wb:
                    opcode = d_mem_wb.get("opcode", 0)
                    if opcode == 0b1101111 or opcode == 0b1100111:
                        return True, mem_wb.get("wb_val_for_jumps", 0)
                # Check if it's a load
                if is_load_c(c_mem_wb):
                    return True, mem_wb.get("mem_data", 0)
                return True, mem_wb.get("alu_res", 0)
 
    return False, 0


def load_use_hazard(if_id, id_ex):
    
    if not id_ex["valid"]:
        return False
    
    if not if_id["valid"]:
        return False
    
    # Check if ID/EX is a load
    c_id_ex = id_ex.get("c")
    if not is_load_c(c_id_ex):
        return False
    
    # Get the destination register of the load
    rd_load = id_ex.get("rd", 0)
    if rd_load == 0:
        return False
    
    # Check if IF/ID uses rd_load
    d_if_id = None
    if if_id.get("instr") != 0:
        d_if_id = decode(if_id.get("instr", 0))
    
    if d_if_id:
        # Check if rs1 or rs2 matches rd_load
        if uses_rs1(d_if_id) and d_if_id.get("rs1") == rd_load:
            return True
        if uses_rs2(d_if_id) and d_if_id.get("rs2") == rd_load:
            return True
    
    return False


# ------------------------------------------------------------
# Trace helpers
# ------------------------------------------------------------

def try_mnemonic(d):
    
    if d is None or d.get("instr") == 0:
        return "NOP"
 
    opcode = d.get("opcode", 0)
    funct3 = d.get("funct3", 0)
    funct7 = d.get("funct7", 0)
 
    # R-type
    if opcode == 0b0110011:
        if funct3 == 0b000:
            return "sub" if funct7 == 0b0100000 else "add"
        elif funct3 == 0b001:
            return "sll"
        elif funct3 == 0b010:
            return "slt"
        elif funct3 == 0b011:
            return "sltu"
        elif funct3 == 0b100:
            return "xor"
        elif funct3 == 0b101:
            return "sra" if funct7 == 0b0100000 else "srl"
        elif funct3 == 0b110:
            return "or"
        elif funct3 == 0b111:
            return "and"
 
    # I-type ALU
    if opcode == 0b0010011:
        if funct3 == 0b000:
            return "addi"
        elif funct3 == 0b010:
            return "slti"
        elif funct3 == 0b011:
            return "sltiu"
        elif funct3 == 0b100:
            return "xori"
        elif funct3 == 0b110:
            return "ori"
        elif funct3 == 0b111:
            return "andi"
        elif funct3 == 0b001:
            return "slli"
        elif funct3 == 0b101:
            return "srai" if funct7 == 0b0100000 else "srli"
 
    # Load/Store
    if opcode == 0b0000011 and funct3 == 0b010:
        return "lw"
    if opcode == 0b0100011 and funct3 == 0b010:
        return "sw"
 
    # Branch
    if opcode == 0b1100011:
        if funct3 == 0b000:
            return "beq"
        elif funct3 == 0b001:
            return "bne"
        elif funct3 == 0b100:
            return "blt"
        elif funct3 == 0b101:
            return "bge"
        elif funct3 == 0b110:
            return "bltu"
        elif funct3 == 0b111:
            return "bgeu"
 
    # Jump
    if opcode == 0b1101111:
        return "jal"
    if opcode == 0b1100111 and funct3 == 0b000:
        return "jalr"
 
    return "NOP"


def trace_cycle(cycle, pc, stall, flush, if_id, id_ex, ex_mem, mem_wb, wb_info):
   
    if_id_mnem = try_mnemonic(decode(if_id.get("instr", 0))) if if_id.get("valid") else "---"
    id_ex_mnem = try_mnemonic(id_ex.get("d")) if id_ex.get("valid") else "---"
    ex_mem_mnem = try_mnemonic(ex_mem.get("d")) if ex_mem.get("valid") else "---"
    mem_wb_mnem = try_mnemonic(mem_wb.get("d")) if mem_wb.get("valid") else "---"
 
    trace_line = (
        f"cycle={cycle:4d} pc=0x{pc:08X} stall={stall} flush={flush} | "
        f"IF/ID={if_id_mnem:6s} | ID/EX={id_ex_mnem:6s} | "
        f"EX/MEM={ex_mem_mnem:6s} | MEM/WB={mem_wb_mnem:6s}"
    )
 
    if wb_info:
        trace_line += f" | {wb_info}"
 
    return trace_line


# ------------------------------------------------------------
# Program loader + log writers
# ------------------------------------------------------------

def load_imem_from_file(path):
    """Given."""
    imem = {}
    pc = 0
    f = open(path, "r", encoding="utf-8")
    for line in f:
        s = line.strip()
        if not s:
            continue
        if s.startswith("#"):
            continue
        if s.lower().startswith("0x"):
            s = s[2:]
        instr = int(s, 16) & MASK32
        imem[pc] = instr
        pc += 4
    f.close()
    return imem


def write_trace_log(lines, path):
    f = open(path, "w", encoding="utf-8")
    for ln in lines:
        f.write(ln + "\n")
    f.close()


def write_regs_log(regs, path):
    f = open(path, "w", encoding="utf-8")
    for i in range(32):
        f.write("x%-2d = 0x%08X (%d)\n" % (i, u32(regs[i]), s32(regs[i])))
    f.close()


def write_dmem_log(dmem, path):
    f = open(path, "w", encoding="utf-8")
    for a in sorted(dmem.keys()):
        f.write("0x%08X : 0x%08X (%d)\n" % (u32(a), u32(dmem[a]), s32(dmem[a])))
    f.close()


# ------------------------------------------------------------
# Main pipeline simulation loop
# ------------------------------------------------------------

def main():

     # ===== HAZARD DETECTION: Initialize performance tracker =====
    hazard_detector = HazardDetector()
    # ===== END HAZARD DETECTION SECTION =====

    imem = load_imem_from_file("hex_inst.txt")

    regs = [0] * 32
    dmem = {}

    pc = 0
    cycle = 0
    max_cycles = 50_000_000

    # Pipeline registers (latched at end of each cycle)
    if_id = make_if_id()
    id_ex = make_id_ex()
    ex_mem = make_ex_mem()
    mem_wb = make_mem_wb()

    trace_lines = []
    fetching_done = False

    while cycle < max_cycles:

        # ===== HAZARD DETECTION: Detect RAW hazards at start of cycle =====
        raw_hazard_detected, hazard_reg = detect_raw_hazard(
            if_id.get("instr", 0), id_ex, ex_mem, mem_wb, 
            hazard_detector, cycle
        )
        # ===== END HAZARD DETECTION SECTION ====

        # ------------------------------------------------------------
        # WB stage (commit architectural state)
        # ------------------------------------------------------------
        wb_info = ""
        
        if mem_wb["valid"] and will_write_c(mem_wb.get("c")):
            # Determine write-back value
            c_wb = mem_wb.get("c")
            d_wb = mem_wb.get("d")
            
            if d_wb and (d_wb.get("opcode") == 0b1101111 or d_wb.get("opcode") == 0b1100111):
                # Jump instruction: write pc+4
                wb_val = mem_wb.get("wb_val_for_jumps", 0)
            elif c_wb.get("MemToReg", 0):
                # Load: write memory data
                wb_val = mem_wb.get("mem_data", 0)
            else:
                # ALU result
                wb_val = mem_wb.get("alu_res", 0)
 
            rd = mem_wb.get("rd", 0)
            if rd != 0:
                regs[rd] = u32(wb_val)
                wb_info = f"WB:x{rd}<-0x{u32(wb_val):08X}"
 
        # Always ensure x0 = 0
        regs[0] = 0

        # ------------------------------------------------------------
        # MEM stage (data memory access)
        # ------------------------------------------------------------
        next_mem_wb = make_mem_wb()
       
        if ex_mem["valid"]:
            c_mem = ex_mem.get("c")
            d_mem = ex_mem.get("d")
            
            # Pass through to MEM/WB
            next_mem_wb["valid"] = 1
            next_mem_wb["c"] = c_mem
            next_mem_wb["d"] = d_mem
            next_mem_wb["rd"] = ex_mem.get("rd", 0)
            next_mem_wb["alu_res"] = ex_mem.get("alu_res", 0)
            next_mem_wb["pc_plus4"] = ex_mem.get("pc_plus4", 0)
            next_mem_wb["wb_val_for_jumps"] = ex_mem.get("wb_val_for_jumps", 0)
 
            # Memory access
            if c_mem and c_mem.get("MemRead", 0):
                # Load
                mem_addr = ex_mem.get("mem_addr", 0)
                mem_data = dmem_load_word(dmem, mem_addr)
                next_mem_wb["mem_data"] = mem_data
            elif c_mem and c_mem.get("MemWrite", 0):
                # Store
                mem_addr = ex_mem.get("mem_addr", 0)
                store_data = ex_mem.get("rs2_val_fwd", 0)
                dmem_store_word(dmem, mem_addr, store_data)
        # ------------------------------------------------------------
        # EX stage (ALU + branch/jump resolution + forwarding)
        # ------------------------------------------------------------
        next_ex_mem = make_ex_mem()
        flush = False
        redirect_pc = 0
        
        if id_ex["valid"]:
            c_ex = id_ex.get("c")
            d_ex = id_ex.get("d")
            pc_ex = id_ex.get("pc", 0)
            pc_plus4_ex = id_ex.get("pc_plus4", 0)
            imm_ex = id_ex.get("imm", 0)
            rs1_ex = id_ex.get("rs1", 0)
            rs2_ex = id_ex.get("rs2", 0)
            rd_ex = id_ex.get("rd", 0)
            rs1_val_ex = id_ex.get("rs1_val", 0)
            rs2_val_ex = id_ex.get("rs2_val", 0)
            alu_op_ex = id_ex.get("alu_op", "ADD")
 
            # Forwarding for rs1
            use_fwd_rs1, fwd_rs1_val = forwarding_select(rs1_ex, ex_mem, mem_wb)
            if use_fwd_rs1:
                rs1_val_ex = fwd_rs1_val
 
            # Forwarding for rs2
            use_fwd_rs2, fwd_rs2_val = forwarding_select(rs2_ex, ex_mem, mem_wb)
            if use_fwd_rs2:
                rs2_val_ex = fwd_rs2_val
 
            # Select ALU input 2
            if c_ex.get("ALUSrc", 0):
                alu_in2 = imm_ex
            else:
                alu_in2 = rs2_val_ex
 
            # ALU execution
            alu_res = alu_exec(alu_op_ex, rs1_val_ex, alu_in2)
            store_data = rs2_val_ex  # For sw, use original rs2 (before forwarding used for address)
 
            # Branch/Jump resolution
            next_pc = pc_plus4_ex
            branch_taken_flag = False
            wb_val_jump = pc_plus4_ex
 
            if c_ex.get("Branch", 0):
                # Branch
                br_type = c_ex.get("BrType")
                if branch_taken(br_type, rs1_val_ex, rs2_val_ex):
                    branch_taken_flag = True
                    next_pc = u32(pc_ex + imm_ex)
                    flush = True
                    redirect_pc = next_pc
 
            if c_ex.get("Jump", 0):
                # Jump
                branch_taken_flag = True
                if c_ex.get("JumpReg", 0):
                    # jalr
                    next_pc = u32((rs1_val_ex + imm_ex) & 0xFFFFFFFE)
                else:
                    # jal
                    next_pc = u32(pc_ex + imm_ex)
                flush = True
                redirect_pc = next_pc
 
            # Fill EX/MEM
            next_ex_mem["valid"] = 1
            next_ex_mem["c"] = c_ex
            next_ex_mem["d"] = d_ex
            next_ex_mem["rd"] = rd_ex
            next_ex_mem["alu_res"] = alu_res
            next_ex_mem["rs2_val_fwd"] = store_data
            next_ex_mem["mem_addr"] = alu_res  # Address is ALU result
            next_ex_mem["branch_taken"] = 1 if branch_taken_flag else 0
            next_ex_mem["next_pc"] = next_pc
            next_ex_mem["pc_plus4"] = pc_plus4_ex
            next_ex_mem["wb_val_for_jumps"] = wb_val_jump
        # ------------------------------------------------------------
        # ID stage (decode / reg read) + stall insertion
        # ------------------------------------------------------------
        stall = False

         # ===== HAZARD DETECTION: Use enhanced stall detection =====
        stall = detect_load_use_hazard_enhanced(if_id, id_ex, hazard_detector, cycle)
        # ===== END HAZARD DETECTION SECTION =====
       
        stall = load_use_hazard(if_id, id_ex)
        next_id_ex = make_id_ex()
        
        if not stall and if_id["valid"]:
            instr_id = if_id.get("instr", 0)
            pc_id = if_id.get("pc", 0)
 
            if instr_id != 0:

                  # ===== HAZARD DETECTION: Count non-NOP instructions =====
                hazard_detector.record_instruction()
                # ===== END HAZARD DETECTION SECTION =====

                # Decode
                d_id = decode(instr_id)
                c_id = main_control(d_id)
                imm_id = select_imm(d_id, c_id)
                rs1_id = d_id.get("rs1", 0)
                rs2_id = d_id.get("rs2", 0)
                rd_id = d_id.get("rd", 0)
 
                # Register read
                rs1_val_id = regs[rs1_id]
                rs2_val_id = regs[rs2_id]
 
                # ALU control
                alu_op_id = alu_control(c_id, d_id)
 
                # Fill ID/EX
                next_id_ex["valid"] = 1
                next_id_ex["pc"] = pc_id
                next_id_ex["pc_plus4"] = u32(pc_id + 4)
                next_id_ex["d"] = d_id
                next_id_ex["c"] = c_id
                next_id_ex["imm"] = imm_id
                next_id_ex["rs1"] = rs1_id
                next_id_ex["rs2"] = rs2_id
                next_id_ex["rd"] = rd_id
                next_id_ex["rs1_val"] = rs1_val_id
                next_id_ex["rs2_val"] = rs2_val_id
                next_id_ex["alu_op"] = alu_op_id
 
        if flush:
            # Override ID/EX to bubble on flush
            next_id_ex = make_id_ex()
 
        if stall:
            # Insert bubble into ID/EX on stall
            next_id_ex = make_id_ex()

        # ------------------------------------------------------------
        # IF stage (fetch) + PC update + stall/flush handling
        # ------------------------------------------------------------
        next_if_id = make_if_id()
        
        if flush:
            # Flush: clear IF/ID and redirect PC
            pc = redirect_pc
            next_if_id = make_if_id()
        elif stall:
            # Stall: freeze IF/ID and PC
            next_if_id = if_id
        else:
            # Normal: fetch next instruction
            if not fetching_done:
                if pc in imem:
                    instr = imem[pc]
                    next_if_id["valid"] = 1
                    next_if_id["pc"] = pc
                    next_if_id["instr"] = instr
                    pc = u32(pc + 4)
                else:
                    # End of instruction memory
                    fetching_done = True
                    next_if_id = make_if_id()

        # ------------------------------------------------------------
        # Trace line for this cycle (must be readable)
        # ------------------------------------------------------------
       
        trace_lines.append(
            trace_cycle(
                cycle, pc if not stall else u32(pc - 4), stall, flush,
                if_id, id_ex, ex_mem, mem_wb, wb_info
            )
        )
        # ------------------------------------------------------------
        # Latch pipeline registers (end of cycle)
        # ------------------------------------------------------------
        mem_wb = next_mem_wb
        ex_mem = next_ex_mem
        id_ex = next_id_ex
        if_id = next_if_id

        # ------------------------------------------------------------
        # Halt condition: fetch done + pipeline drained
        # ------------------------------------------------------------
        if fetching_done and not if_id["valid"] and not id_ex["valid"] and not ex_mem["valid"] and not mem_wb["valid"]:
            break
        cycle += 1

    # Write logs
    write_trace_log(trace_lines, "trace.log")
    write_regs_log(regs, "regs_final.log")
    write_dmem_log(dmem, "dmem_final.log")

    print("HALT")
    print("cycles =", cycle)

    # ===== HAZARD DETECTION: Print performance report =====
    hazard_detector.write_report(cycle, "hazard_report.log")
    # ===== END HAZARD DETECTION SECTION =====

   


if __name__ == "__main__":
    main()