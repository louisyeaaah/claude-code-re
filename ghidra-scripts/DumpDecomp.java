// Ghidra headless post-script: 导出函数并反编译为 C。
// 用法（analyzeHeadless 的 -postScript 参数）：
//   -postScript DumpDecomp.java "<函数名过滤子串，可为空>" <输出文件> [每函数超时秒]
import ghidra.app.script.GhidraScript;
import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.FunctionManager;

import java.io.FileWriter;
import java.io.PrintWriter;

public class DumpDecomp extends GhidraScript {
    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        String filter = args.length > 0 ? args[0] : "";
        if (filter.equals("-")) filter = "";   // "-" = 全部函数
        String outPath = args.length > 1 ? args[1] : "decomp.txt";
        int timeout = args.length > 2 ? Integer.parseInt(args[2]) : 90;

        DecompInterface di = new DecompInterface();
        di.toggleCCode(true);
        di.toggleSyntaxTree(false);
        if (!di.openProgram(currentProgram)) {
            println("ERROR: openProgram failed");
            return;
        }
        PrintWriter pw = new PrintWriter(new FileWriter(outPath));
        pw.println("// program: " + currentProgram.getName());
        pw.println("// filter : " + (filter.isEmpty() ? "(all)" : filter));
        pw.println();

        FunctionManager fm = currentProgram.getFunctionManager();
        int total = 0, ok = 0;
        for (Function f : fm.getFunctions(true)) {
            if (!filter.isEmpty() && !f.getName().contains(filter)) continue;
            total++;
            pw.println("// ==== " + f.getName() + " @ " + f.getEntryPoint()
                    + "  (params=" + f.getParameterCount() + ", size=" + f.getBody().getNumAddresses() + ") ====");
            try {
                DecompileResults r = di.decompileFunction(f, timeout, monitor);
                if (r != null && r.decompileCompleted() && r.getDecompiledFunction() != null) {
                    pw.println(r.getDecompiledFunction().getC());
                    ok++;
                } else {
                    pw.println("// [decompile incomplete] " + (r == null ? "null" : r.getErrorMessage()));
                }
            } catch (Exception e) {
                pw.println("// [decompile error] " + e);
            }
            pw.println();
        }
        pw.close();
        di.dispose();
        println("DumpDecomp: matched=" + total + " decompiled=" + ok + " -> " + outPath);
    }
}
