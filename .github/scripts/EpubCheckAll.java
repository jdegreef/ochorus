import com.adobe.epubcheck.tool.EpubChecker;

import java.io.File;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;

/**
 * Every EPUB in a directory through epubcheck, in ONE JVM.
 *
 * epubcheck's CLI takes one file per run, and CI used to start a JVM per book:
 * ~140 JVM start-ups and JIT warm-ups were nearly all of the job's eight
 * minutes, while a warm JVM checks a book in a fraction of a second (all 138
 * locally: 139 s one JVM each, 4 at a time -> 7 s here). This calls the CLI's
 * own entry point (EpubChecker.run, the method `main` wraps) once per file, so
 * the arguments, the `-q` error lines and each book's verdict are exactly the
 * CLI's. One book after another, deliberately: epubcheck doesn't promise its
 * checkers are safe side by side on threads, and a pool saved ~3 s.
 *
 *   java -cp epubcheck.jar EpubCheckAll.java <dir>
 *
 * Exits non-zero, naming each failing book as a GitHub error annotation, if any
 * book fails — or if the directory holds no EPUBs at all, so an export that
 * silently wrote nothing can't pass as "nothing failed".
 */
public class EpubCheckAll {
    public static void main(String[] args) {
        File[] books = new File(args[0]).listFiles((dir, name) -> name.endsWith(".epub"));
        if (books == null || books.length == 0) {
            System.out.println("::error::no .epub files in " + args[0]);
            System.exit(2);
        }
        Arrays.sort(books);
        List<String> failed = new ArrayList<>();
        for (File book : books) {
            if (new EpubChecker().run(new String[] {"-q", book.getPath()}) != 0) {
                failed.add(book.getName());
            }
        }
        for (String name : failed) System.out.println("::error::epubcheck failed: " + name);
        System.out.println(books.length + " EPUBs checked, " + failed.size() + " failed.");
        System.exit(failed.isEmpty() ? 0 : 1);
    }
}
