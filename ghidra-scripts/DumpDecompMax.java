// Ghidra headless post-script（"榨干预算"版）
//   1) 放宽每函数反编译超时（默认 1200s）
//   2) 放宽跳转表条目上限（DecompileOptions.setMaxJumpTableEntries，默认 1024 → 16384）
//   3) 放宽指令数 / payload 资源上限
//   4) 记录每个函数耗时，把慢函数单独列表
//
// 用法：-postScript DumpDecompMax.java "<过滤，- 表示全部>" <输出文件> [超时秒] [慢阈值秒]
import ghidra.app.script.GhidraScript;
import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileOptions;
import ghidra.app.decompiler.DecompileResults;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.FunctionManager;

import java.io.FileWriter;
import java.io.PrintWriter;

public class DumpDecompMax extends GhidraScript {
    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        String filter = args.length > 0 ? args[0] : "-";
        if (filter.equals("-")) filter = "";
        String outPath = args.length > 1 ? args[1] : "decomp-max.txt";
        int timeout = args.length > 2 ? Integer.parseInt(args[2]) : 1200;
        int slowThreshold = args.length > 3 ? Integer.parseInt(args[3]) : 30;

        DecompileOptions dopts = new DecompileOptions();
        dopts.setDefaultTimeout(timeout);
        dopts.setMaxJumpTableEntries(16384);     // 默认 1024
        dopts.setMaxInstructions(20_000_000);
        dopts.setMaxPayloadMBytes(512);

        DecompInterface di = new DecompInterface();
        di.toggleCCode(true);
        di.toggleSyntaxTree(false);
        di.setOptions(dopts);

        if (!di.openProgram(currentProgram)) {
            println("ERROR: openProgram failed");
            return;
        }

        PrintWriter pw = new PrintWriter(new FileWriter(outPath));
        PrintWriter slow = new PrintWriter(new FileWriter(outPath + ".slow.txt"));
        pw.println("// program: " + currentProgram.getName());
        pw.println("// filter : " + (filter.isEmpty() ? "(all)" : filter));
        pw.println("// budget : timeout=" + timeout + "s  maxJumptableEntries=16384  maxInstructions=20M  maxPayload=512MB");
        pw.println();
        slow.println("# functions taking >= " + slowThreshold + "s");
        slow.println("# seconds\taddress\tname\tsize_bytes");

        FunctionManager fm = currentProgram.getFunctionManager();
        int total = 0, ok = 0, slowCount = 0;
        long worst = 0;
        String worstName = "";
        for (Function f : fm.getFunctions(true)) {
            if (!filter.isEmpty() && !f.getName().contains(filter)) continue;
            total++;
            long t0 = System.currentTimeMillis();
            pw.println("// ==== " + f.getName() + " @ " + f.getEntryPoint()
                    + "  (params=" + f.getParameterCount() + ", size=" + f.getBody().getNumAddresses() + ") ====");
            try {
                DecompileResults r = di.decompileFunction(f, timeout, monitor);
                if (r != null && r.decompileCompleted() && r.getDecompiledFunction() != null) {
                    pw.println(r.getDecompiledFunction().getC());
                    ok++;
                    String msg = r.getErrorMessage();
                    if (msg != null && !msg.isEmpty()) pw.println("// [decompiler message] " + msg);
                } else {
                    pw.println("// [decompile incomplete] " + (r == null ? "null" : r.getErrorMessage()));
                }
            } catch (Exception e) {
                pw.println("// [decompile error] " + e);
            }
            long dt = (System.currentTimeMillis() - t0) / 1000;
            if (dt >= slowThreshold) {
                slowCount++;
                slow.println(dt + "\t" + f.getEntryPoint() + "\t" + f.getName() + "\t" + f.getBody().getNumAddresses());
            }
            if (dt > worst) { worst = dt; worstName = f.getName(); }
            pw.println();
        }
        pw.close();
        slow.close();
        di.dispose();
        println("DumpDecompMax: matched=" + total + " decompiled=" + ok
                + " slow(>=" + slowThreshold + "s)=" + slowCount
                + " worst=" + worst + "s (" + worstName + ") -> " + outPath);
    }
}
