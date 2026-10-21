#!/usr/bin/perl

# selftest-compareresults.pl <new data> <reference data>

use strict;

my $retstatus = 0;
# SHAPE-03: AN EMPTY ACCUMULATOR MUST NOT READ AS SUCCESS (OC-66).
#
# This script is SHAPE-03's own worked example: it iterated the REFERENCE hash,
# so a 0-byte reference produced zero comparisons, an untouched $retstatus and
# "selftest: PASS" (OC-4). The second loop below -- flagging new keys with no
# reference -- closed that, and the reference-key loop flags the mirror case, so
# a single empty side is now caught (measured: exit 1 either way).
#
# What remained was BOTH sides empty: zero comparisons, exit 0, "Maximum delta:
# 0" -- measured reachable today. It needs a corrupted reference, which the
# fixture manifest's digests also guard, but a comparison tool must not report
# agreement when it compared nothing. Count the comparisons and refuse zero.
my $compared = 0;

my $epsilon = 1.0E-10;
my $maxdelta = 0;

# IDENTITY IS COMPARED, NOT DISCARDED (OC-74).
#
# The line filter below selects only lines matching
# /(Estimate:|Assessed|^H_original|^H_bitstring)/i, so the first two lines of
# every report -- "Opening file: '<path>'" and "Loaded N samples of K distinct
# W-bit-wide symbols" -- were never compared. This comparator therefore could
# not tell that the output it read came from the same input, at the same sample
# count, at the same symbol width, as the reference it was checking against.
#
# MEASURED: a copy of refdata/normal.res with its identity lines rewritten to
# claim "SOME-OTHER-FILE.bin" and "42 samples of 3 distinct 2-bit-wide symbols"
# compared EQUAL to normal.bin's real output (1,000,000 samples, 179 distinct
# 8-bit symbols): "Maximum delta: 6.93e-15", 98 values compared, exit 0.
#
# That is the flagship self-test's comparator, and `selftest` pairs each output
# with a reference by a FILENAME TRANSFORM alone, so a mispaired reference is
# precisely the case it could not see. An exclusion that touches the input's
# identity does not weaken a comparison, it voids it: agreement becomes
# indistinguishable from a category error (instrument rule 8).
sub identity_of {
    my ($path) = @_;
    open my $fh, '<', $path or die "Can't open $path: $!";
    my %id;
    while (my $l = <$fh>) {
        # BOTH WORDINGS. The tool now prints "Loaded file: '<path>' (SHA-256
        # hash ...)"; the committed references, which predate that change, say
        # "Opening file: '<path>'". Same field, two spellings -- so this is
        # matched on the field, not on one side's wording, which is instrument
        # rule 3's corollary applied to a comparator's own input.
        if ($l =~ m{^(?:Opening|Loaded) file:\s*'([^']+)'}) {
            my $p = $1; $p =~ s{.*/}{};          # basename: the directory may
            $id{file} = $p;                      # legitimately differ
        } elsif ($l =~ /^Loaded\s+(\d+)\s+samples\s+of\s+(\d+)\s+distinct\s+(\d+)-bit/) {
            @id{qw(samples distinct width)} = ($1, $2, $3);
        }
        last if exists $id{file} && exists $id{samples};
    }
    close $fh;
    return \%id;
}

my $id_new = identity_of($ARGV[0]);
my $id_ref = identity_of($ARGV[1]);
for my $k (qw(file samples distinct width)) {
    if (!defined $id_new->{$k} || !defined $id_ref->{$k}) {
        print "$ARGV[0]: REFUSING: identity field '$k' is absent from one side\n";
        print "  (output: ", ($id_new->{$k} // 'MISSING'), "; reference: ",
              ($id_ref->{$k} // 'MISSING'), ")\n";
        print "  A comparison that cannot establish it read the same input cannot\n";
        print "  distinguish agreement from a category error (OC-74).\n";
        exit 2;
    }
    if ($id_new->{$k} ne $id_ref->{$k}) {
        print "$ARGV[0]: IDENTITY MISMATCH on '$k': output '$id_new->{$k}' vs reference '$id_ref->{$k}'\n";
        print "  The numbers below, agreeing or not, are about different things.\n";
        $retstatus = 1;
    }
}

open my $local_fh, '<', $ARGV[0] or die "Can't open $ARGV[0]: $!";
my $newResults = resultsHash($local_fh);
close $local_fh;

open my $local_reffh, '<', $ARGV[1] or die "Can't open $ARGV[1]: $!";
my $refResults = resultsHash($local_reffh);
close $local_reffh;

foreach my $refKey (keys %$refResults) {
   if(exists($newResults->{$refKey})) {
      $compared++;
      my $maxval = (abs($refResults->{$refKey})>=abs($newResults->{$refKey})?abs($refResults->{$refKey}):abs($newResults->{$refKey}));

      my $absdelta = abs($refResults->{$refKey} - $newResults->{$refKey});

      my $reldelta;
      my $delta;

      #print "item: $refKey\n";

      if($maxval > 0.0) {
      	$reldelta = $absdelta / $maxval;
      } else {
        $reldelta = 0.0;
      }

      $delta = ($absdelta <= $reldelta) ? $absdelta : $reldelta;
      if($delta > $maxdelta) {
         $maxdelta = $delta;
      }

      if($delta >= $epsilon) {
         print "$ARGV[0]: Significant difference for $refKey (reference: $refResults->{$refKey} new: $newResults->{$refKey} delta: $delta)\n";
         $retstatus = 1;
      } 
      delete $newResults->{$refKey};
   } else {
      print "$ARGV[0]: No corresponding value for $refKey\n";
      $retstatus = 1;
   }
}

# Keys left in %$newResults are those the output produced and the reference does
# not contain: every key the reference did have was deleted above as it was
# compared. Such a key has been compared against NOTHING.
#
# This used to print and return success. The loop above iterates the REFERENCE
# key set, so the comparison was total in one direction only: a key missing from
# the output failed ("No corresponding value"), while a key missing from the
# REFERENCE was announced on stdout and ignored. A comparison that must be total
# has to assert the two key sets are EQUAL, not iterate one of them.
#
# That asymmetry was not hypothetical. This script was extended to collect the
# final combined figures -- see resultsHash below, which names "dropping the
# n x H_bitstring term" as the fault that extension exists to catch -- but the
# reference files were never regenerated, so "H_bitstring Per Symbol" is emitted
# on 6 of the 11 selftest files, appears in 0 of the references, and was
# therefore checked on none of them. The one collected key with no reference was
# the exact term the extension was written for.
#
# An extra key is now a FAILURE. Enabling this makes the shipped references fail
# on those 6 files, which is the correct report: the comparison has been
# incomplete since the collection was added and nothing said so. Do not silence
# this to keep the suite green -- see audits/2026-10-11-independent-audit
# (OC-20, OC-21) for why the references must not simply be regenerated from the
# current tools.
foreach my $newKey (keys %$newResults) {
   print "$ARGV[0]: No reference value for $newKey (output has it, reference does not): $newResults->{$newKey}\n";
   $retstatus = 1;
}

print "Maximum delta: $maxdelta\n";
if($compared == 0) {
   print "$ARGV[0]: NO COMPARISONS WERE MADE. Both the output and the reference\n";
   print "  yielded zero keys, so agreement here is vacuous (SHAPE-03, OC-66).\n";
   exit 2;
}
printf "%s: %d value(s) compared; identity %s / %s samples / %s-bit matched\n",
    $ARGV[0], $compared, $id_new->{file}, $id_new->{samples}, $id_new->{width};
exit $retstatus;

sub resultsHash {
   my $fd = shift;
   my %input;

   # Two kinds of line are collected:
   #
   #  1. per-estimator values, e.g.
   #        Literal Collision Estimate: min entropy = 0.126...
   #
   #  2. the final combined figures produced by main() rather than by any
   #     estimator:
   #        H_bitstring = <v>
   #        H_bitstring Per Symbol = <v>
   #        H_original = <v>
   #        Assessed min entropy: <v>
   #
   # Group 2 was previously not collected at all, so a fault confined to the
   # final combination (for instance dropping the n x H_bitstring term, or
   # failing to fold in H_original) left every collected value unchanged and
   # the comparison passed. The final figure is the number an assessment is
   # actually reported with, so it is the one that most needs checking.
   while( my $line = <$fd> ) {
      if ( $line =~ /(Estimate:|Assessed|^H_original|^H_bitstring)/i ) {
         # "<label> = <value>" covers the estimators and H_original /
         # H_bitstring; "<label>: <value>" covers "Assessed min entropy".
         # The " = " form is tried first so that estimator lines, which
         # contain both separators, keep the labels they have always had.
         if(($line =~ /^([^=]+) = ([-+]?[0-9]*\.?[0-9]+([eE][-+]?[0-9]+)?)$/ ) ||
            ($line =~ /^([^:=]+): ([-+]?[0-9]*\.?[0-9]+([eE][-+]?[0-9]+)?)$/ )) {
            my $label = $1;
            my $value = $2;

            $label =~ s/\s*$//;

            $input{"$label"} = $value;
            #print "$label -> $value\n";
         } 
      } 
   }

  return \%input; # return hash reference
}

