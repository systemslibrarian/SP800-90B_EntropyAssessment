#!/usr/bin/perl

# selftest-compareresults.pl <new data> <reference data>

use strict;

my $retstatus = 0;

my $epsilon = 1.0E-10;
my $maxdelta = 0;

open my $local_fh, '<', $ARGV[0] or die "Can't open $ARGV[0]: $!";
my $newResults = resultsHash($local_fh);
close $local_fh;

open my $local_reffh, '<', $ARGV[1] or die "Can't open $ARGV[1]: $!";
my $refResults = resultsHash($local_reffh);
close $local_reffh;

foreach my $refKey (keys %$refResults) {
   if(exists($newResults->{$refKey})) {
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

