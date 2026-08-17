import javax.swing.*;
import java.awt.*;

/** Controlled Swing probe for the macOS Tier F re-run (pipeline-tap campaign).
 *
 *  The first run confounded two things: it set an accessibleName on every
 *  component, so "the channel reports the name instead of the painted text"
 *  could not be distinguished from "the probe told it to". This version puts
 *  BOTH variants in one window so the comparison is within-subject:
 *
 *    - components suffixed NAMED  call setAccessibleName(...)  (as before)
 *    - components suffixed PLAIN  are left exactly as Swing builds them
 *
 *  Same for the buttons, because the act-side result (AXPress returns 0 while
 *  nothing happens) must be checked against a button whose name was never
 *  touched before it can be blamed on the platform.
 */
public class SwingProbe2 {
    static JLabel counterNamed = new JLabel("countNamed=0");
    static JLabel counterPlain = new JLabel("countPlain=0");
    static int nNamed = 0, nPlain = 0;

    public static void main(String[] args) {
        SwingUtilities.invokeLater(() -> {
            JFrame f = new JFrame("swing probe 2");
            f.setDefaultCloseOperation(JFrame.EXIT_ON_CLOSE);
            JPanel p = new JPanel();
            p.setLayout(new BoxLayout(p, BoxLayout.Y_AXIS));

            // --- variant A: accessibleName set (what the first run did) ---
            JLabel sentinelNamed = new JLabel("SENTINEL-NAMED alpha");
            sentinelNamed.getAccessibleContext().setAccessibleName("sentinel-label");
            counterNamed.getAccessibleContext().setAccessibleName("counter-label");
            JButton bumpNamed = new JButton("IncrementNamed");
            bumpNamed.getAccessibleContext().setAccessibleName("increment-button");
            bumpNamed.addActionListener(e -> counterNamed.setText("countNamed=" + (++nNamed)));

            // --- variant B: untouched, exactly as Swing builds it ---
            JLabel sentinelPlain = new JLabel("SENTINEL-PLAIN bravo");
            JButton bumpPlain = new JButton("IncrementPlain");
            bumpPlain.addActionListener(e -> counterPlain.setText("countPlain=" + (++nPlain)));

            p.add(sentinelNamed); p.add(counterNamed); p.add(bumpNamed);
            p.add(Box.createVerticalStrut(12));
            p.add(sentinelPlain); p.add(counterPlain); p.add(bumpPlain);

            f.getContentPane().add(p);
            f.setSize(420, 300);
            f.setLocation(60, 120);
            f.setVisible(true);
        });
    }
}
