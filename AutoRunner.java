import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.time.LocalDateTime;
import java.util.concurrent.Executors;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.TimeUnit;

public class AutoRunner {

    private static final int INTERVAL_SECONDS = 600; // 每 10 分鐘

    public static void main(String[] args) {
        ScheduledExecutorService scheduler = Executors.newSingleThreadScheduledExecutor();

        Runnable task = () -> {
            System.out.println("\n[" + LocalDateTime.now() + "] ⏱ 正在檢查是否有變動...");

            try {
                if (hasGitChanges()) {
                    System.out.println("📂 偵測到有變動，開始執行爬蟲...");
                    runCommand("python crawler.py");

                    System.out.println("📤 推送變更中...");
                    runCommand("git add .");
                    runCommand("git commit -m \"Auto commit\"");
                    runCommand("git push");

                    System.out.println("✅ 成功 Push 到 GitHub！");
                } else {
                    System.out.println("🟡 沒有變動，跳過爬蟲與推送。");
                }
            } catch (Exception e) {
                System.out.println("⚠️ 發生錯誤：" + e.getMessage());
            }

            System.out.println("⏳ 等待 " + INTERVAL_SECONDS + " 秒後繼續...");
        };

        scheduler.scheduleAtFixedRate(task, 0, INTERVAL_SECONDS, TimeUnit.SECONDS);
    }

    private static boolean hasGitChanges() throws Exception {
        Process process = Runtime.getRuntime().exec("git status --porcelain");
        BufferedReader reader = new BufferedReader(new InputStreamReader(process.getInputStream()));
        String line;
        while ((line = reader.readLine()) != null) {
            if (!line.trim().isEmpty()) return true;
        }
        return false;
    }

    private static void runCommand(String command) throws Exception {
        Process process = Runtime.getRuntime().exec(command);
        process.waitFor();
    }
}
