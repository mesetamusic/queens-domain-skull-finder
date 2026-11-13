<#
  Queen's Domain - Silver Skull tracker (69 "Strange Silver Etched Skulls")

  The game has no in-game skull counter, so this script keeps its own checklist.
  Progress is saved to skulls-progress.json next to this script.

  Usage:
    .\skulls.ps1                  show every skull you're MISSING, grouped by area
    .\skulls.ps1 found 3 10 15    mark skulls as collected
    .\skulls.ps1 unfound 10       un-mark a skull
    .\skulls.ps1 area deimpo      show all skulls (found + missing) in one area
    .\skulls.ps1 all              show the full list with check marks
    .\skulls.ps1 reset            clear all progress

  Numbering follows queensdomainmap.com/silver-skulls. Hints are paraphrased from that
  page and from Zer0's Steam guide; entries marked (?) are best-guess matches.
#>
param(
    [Parameter(Position = 0)][string]$Command = 'missing',
    [Parameter(Position = 1, ValueFromRemainingArguments = $true)][string[]]$Args2
)

$Skulls = @(
  # --- Isle of Neasied ---
  @{N=1;  A='Isle of Neasied'; T="Chef's chimney islet"; H="Past the Cemetery Precipice monument, from the Mossy Golem cliff ledge use a Star Lizard to hop out to the islets. Skull is on top of the chef's chimney."; R='All 5 Wind Gems'}
  @{N=2;  A='Isle of Neasied'; T='Spire beside Wing Altar'; H='Fly up the blue-flame spire next to the island Wing Altar; skull is in the broken crevice near the top.'; R='Flight (Flying Mushroom Fossil)'}
  @{N=3;  A='Isle of Neasied'; T='Endu Shrine sword altar'; H='Room where you take Holy Sword Endu after the Shrine Guardian. On top of the sword altar.'; R=''}
  @{N=4;  A='Isle of Neasied'; T="Roof of Wodaso's house"; H="Outer island beyond the chimney islet - round house on the beach (chest has the Wodaso Lens). Skull is on the roof."; R='All 5 Wind Gems'}
  @{N=57; A='Isle of Neasied'; T='Block below Halls lift top'; H='Underground below the island: at Halls Shrouded in Darkness monument ride the lift up, drop two floors onto a stone block (secret wall to its left).'; R=''}
  @{N=58; A='Isle of Neasied'; T='Pipe over Velvet vault door'; H='From Halls Shrouded in Darkness, ride the lift down to the Velvet vault door; skull is on the stone pipe above it.'; R='Flight'}
  # --- Obmuer Temple ---
  @{N=5;  A='Obmuer Temple'; T='Pitch-dark secret room'; H='Past Sacred Cistern monument, dark room: climb to the upper platform and open the secret wall by the skeleton.'; R='Light source'}
  @{N=6;  A='Obmuer Temple'; T='Under the big elevator'; H='Elevator Room monument (after Dagoom). Look underneath the elevator platform from the bottom of the shaft.'; R='Defeat Dagoom'}
  @{N=7;  A='Obmuer Temple'; T='Below first tiara platform'; H='From the temple Wing Altar take the left stairs to the roof, Cestus double-jump to the Stone Tiara 1 platform, drop off the far side.'; R='Cestus'}
  @{N=8;  A='Obmuer Temple'; T='Behind the Wind Gem gazebo'; H='Fly to the area behind the Obmuer Wind Gem gazebo (sarcophagus with the Gold Nautilus Tiara).'; R='True Holy Sword Akunra'}
  @{N=9;  A='Obmuer Temple'; T="Above royal guards' room"; H='Room before the Dagoom arena (Yepo/Erda/Wami fight) - top right corner, fly across.'; R='4+ Wind Gems'}
  # --- Tower of Knowledge ---
  @{N=10; A='Tower of Knowledge'; T='Pipe by three gargoyles'; H='From the Foyer monument drop through the trapdoor to the basement, go right; on top of the stone pipe near three gargoyle statues.'; R=''}
  @{N=11; A='Tower of Knowledge'; T='Ledge under Wing Altar balcony'; H='Ledge beneath the Tower Wing Altar balcony.'; R=''}
  @{N=12; A='Tower of Knowledge'; T='Under the wooden roof stairs'; H='(?) Near ground level - hop the fence and dash under the wooden stairs.'; R=''}
  @{N=13; A='Tower of Knowledge'; T='Spire above Tower exit'; H='(?) Outside, above the doorway that leads onto the bridge to the Mausoleum.'; R=''}
  @{N=14; A='Tower of Knowledge'; T='Rooftop chest'; H='Very top of the Tower of Knowledge.'; R='Flight'}
  # --- Deimpo & Mausoleum ---
  @{N=15; A='Deimpo Mausoleum'; T='Entrance broken pillar'; H='Cross the big bridge from the Tower; on the left-most broken pillar in front of the Mausoleum entrance.'; R=''}
  @{N=16; A='Deimpo Mausoleum'; T='Rock at foot of hill'; H='On a rock at the bottom of the hill outside.'; R=''}
  @{N=17; A='Deimpo Mausoleum'; T='Spire mid big bridge'; H='On top of one of the towers along the Tower-to-Mausoleum bridge.'; R=''}
  @{N=18; A='Deimpo Mausoleum'; T='Clay pots behind double wall'; H='(?) Mausoleum staircase where the first spider appears - behind a double secret wall.'; R='Secret walls'}
  @{N=19; A='Deimpo Mausoleum'; T='Sarcophagus behind gem statue'; H='(?) Open sarcophagus behind the secret wall next to the bat-orb statue.'; R='Secret wall'}
  @{N=20; A='Deimpo Mausoleum'; T="Bowl in Gagi's kitchen"; H="(?) In a bowl/pot inside the cook's kitchen."; R=''}
  @{N=21; A='Deimpo Mausoleum'; T='Poenir and Duenir coffin'; H='In the Poenir & Duenir boss room.'; R=''}
  @{N=22; A='Deimpo Mausoleum'; T='Far platform by Wind Gem'; H='Distant platform near the Mausoleum Wind Gem.'; R='Dashes'}
  @{N=23; A='Deimpo Mausoleum'; T='Snake head in sigil room'; H='On top of the snake head statue.'; R=''}
  @{N=24; A='Deimpo Mausoleum'; T='Behind the memento altar'; H='Behind the throne/altar where you place the mementos.'; R=''}
  # --- Ancient World ---
  @{N=25; A='Ancient World'; T='Vent shaft half-level wall'; H='Past Ventilation Shaft monument, drop down the 2nd big shaft to the half-level with a skeleton; secret wall.'; R='Secret wall'}
  @{N=26; A='Ancient World'; T='Rock behind Overlook monument'; H='On a rock behind the Overlook monument.'; R=''}
  @{N=27; A='Ancient World'; T='Rock above pipe'; H='On a rock above a large pipe.'; R=''}
  @{N=28; A='Ancient World'; T='Room above first vent'; H='(?) In the vents - go up from the skeleton at the dead end.'; R=''}
  @{N=29; A='Ancient World'; T='High platform, big island start'; H='High platform where the big island begins.'; R='Dashes/flight'}
  @{N=30; A='Ancient World'; T='Hidden building above Plasma tower'; H='Hidden structure high above the electric/plasma tower.'; R='Flight'}
  @{N=31; A='Ancient World'; T='Distant rooftop from cliff'; H='Far rooftop reached from the cliff facing the castle.'; R='Flight'}
  @{N=32; A='Ancient World'; T='Upper-left platform of rooftop'; H='Upper-left platform on a skyscraper rooftop.'; R='Flight'}
  @{N=33; A='Ancient World'; T='Rock left of castle bridge'; H='On a rock left of the bridge to Siraatsu Castle.'; R=''}
  @{N=34; A='Ancient World'; T='Hollow tree by Wing Altar'; H='Fly up high near the Wing Altar/teleporter and drop into the hollow tree.'; R='Flight'}
  @{N=35; A='Ancient World'; T='Ledge by Besom Cutter tower'; H='Ledge next to the Besom Cutter tower.'; R=''}
  @{N=36; A='Ancient World'; T='Shock Rifle deep-water corridor'; H='Inside the out-of-the-way Shock/Electric Rifle mini-dungeon with the laser eyes. Easy to miss!'; R=''}
  @{N=37; A='Ancient World'; T='Hole above Wind Gem gazebo'; H='Above the 5th Wind Gem gazebo.'; R='Flight'}
  @{N=38; A='Ancient World'; T='High ground by gazebo building'; H='High ground beside the gazebo building.'; R=''}
  @{N=39; A='Ancient World'; T='Platform at Record of Sin gap'; H='Just before dropping down into the Record of Sin.'; R=''}
  # --- Siraatsu Castle ---
  @{N=40; A='Siraatsu Castle'; T='Tank top in Cups storeroom'; H='Bar area before the Elevator Room monument: chalice room in the corner, climb the crates to the top of the metal tank.'; R=''}
  @{N=41; A='Siraatsu Castle'; T='Behind biggest tank, lower pit'; H='Lower junkyard/basement area, behind the largest tank.'; R=''}
  @{N=42; A='Siraatsu Castle'; T='Top of the main hall'; H='High up in the main hall - fly between several ledges.'; R='Flight'}
  @{N=43; A='Siraatsu Castle'; T='Above big red pipe'; H='Above the big red pipe.'; R=''}
  @{N=44; A='Siraatsu Castle'; T='Castle roof via glassless window'; H='Exit through a window with no glass onto the roof.'; R='Flight'}
  @{N=45; A='Siraatsu Castle'; T='Second skull on castle roof'; H='There are two on the castle roof - this is the other one.'; R='Flight'}
  # --- Verdant Hollow ---
  @{N=46; A='Verdant Hollow'; T='Bridge wreckage by Wing Altar'; H='Jump from the front-right of the broken bridge near Cliff Edge monument to the Wing Altar; skull in a crack to the right.'; R=''}
  @{N=47; A='Verdant Hollow'; T='Ledge under broken bridge'; H='Ledge underneath the broken bridge.'; R=''}
  @{N=48; A='Verdant Hollow'; T='Branch beside broken bridge'; H='(?) On a branch - reachable through the secret wall off the Mausoleum secret staircase.'; R=''}
  @{N=49; A='Verdant Hollow'; T='Big branch under hanging building'; H='Large branch under the hanging building.'; R=''}
  @{N=50; A='Verdant Hollow'; T='Treetop below temple bridge'; H='Treetop beneath the temple bridge.'; R=''}
  @{N=51; A='Verdant Hollow'; T='Roof of Abraon module building'; H='(?) On the roof of the building with the sealed Siraatsu-statue door.'; R=''}
  @{N=52; A='Verdant Hollow'; T='Roof of Akunra temple'; H='Roof of the temple where you get True Holy Sword Akunra.'; R=''}
  # --- Forgotten Dungeon ---
  @{N=53; A='Forgotten Dungeon'; T='Fire pillar at dungeon start'; H='Elevator beside Cliff Edge monument to the top (Rusted Cell Key chest); on the fire pillar just past it.'; R=''}
  @{N=54; A='Forgotten Dungeon'; T='Above the goddess statue'; H='Above the goddess statue.'; R=''}
  @{N=55; A='Forgotten Dungeon'; T='Block by Crimson Grotto'; H='Stone block near the Crimson Grotto.'; R=''}
  @{N=56; A='Forgotten Dungeon'; T='Two floors below brick lift'; H='(?) Elevator between the Dungeon and Tower of Knowledge: round room with 3 green torches - near the ceiling.'; R=''}
  # --- Rotting Cavern ---
  @{N=59; A='Rotting Cavern'; T='Gap in wall past Crumbling Fortress'; H='From Crumbling Fortress monument go right, up the slope, left; fly over to the platform behind the stone wall.'; R='Flight'}
  @{N=60; A='Rotting Cavern'; T='Mushroom ring past stone wall'; H='Mushroom ring beyond the stone wall.'; R=''}
  @{N=61; A='Rotting Cavern'; T='On top of the archway'; H='Top of the archway - high up near the double gates.'; R='Flight'}
  @{N=62; A='Rotting Cavern'; T='Boulder opposite first monument'; H='Boulder across from the first monument.'; R=''}
  @{N=63; A='Rotting Cavern'; T='Roof of building opposite'; H='(?) Roof of the building with round windows.'; R='Flight'}
  # --- Record of Sin ---
  @{N=64; A='Record of Sin'; T='4F above Verdant passage'; H='Tower 4F: above the passage leading out to Verdant Hollow.'; R='Defeat Herald of Okbujo'}
  @{N=65; A='Record of Sin'; T='Vines above Herald arena'; H='High on the vines in the Herald boss room (doable without flight using Cestus height).'; R=''}
  @{N=66; A='Record of Sin'; T='Above lowest-floor food'; H='Above the food item on the lowest floor.'; R=''}
  # --- Petrified Garden ---
  @{N=67; A='Petrified Garden'; T='Ring of central statues'; H='Underground near the skull trader gate: middle of the statue ring - climb a small statue.'; R='Break the four seals'}
  @{N=68; A='Petrified Garden'; T='Secret wall at bridge mouth'; H='(?) Opposite the skull trader NPC, on the left behind a secret wall.'; R='Secret wall'}
  # --- Umbada's Trading Outpost ---
  @{N=69; A="Umbada's Outpost"; T='Behind the trading post'; H='Fly from the Deimpo Mausoleum exterior roof to the island; beat the Forgotten Sentinel for the key. Behind the shop.'; R='True Holy Sword Akunra'}
)

$ProgressFile = Join-Path $PSScriptRoot 'skulls-progress.json'

function Load-Found {
    if (Test-Path $ProgressFile) {
        $raw = Get-Content $ProgressFile -Raw
        if ($raw.Trim()) { return @((ConvertFrom-Json $raw) | ForEach-Object { [int]$_ }) }
    }
    return @()
}
function Save-Found($list) {
    $sorted = @($list | Sort-Object -Unique)
    ConvertTo-Json -InputObject $sorted -Compress | Set-Content $ProgressFile
}
function Parse-Numbers($items) {
    $nums = @()
    foreach ($i in $items) {
        foreach ($p in ($i -split '[,\s]+' | Where-Object { $_ })) {
            if ($p -match '^(\d+)-(\d+)$') { $nums += [int]$matches[1]..[int]$matches[2] }
            elseif ($p -match '^\d+$') { $nums += [int]$p }
            else { Write-Host "Ignoring '$p' (not a number)" -ForegroundColor Yellow }
        }
    }
    $bad = $nums | Where-Object { $_ -lt 1 -or $_ -gt 69 }
    if ($bad) { Write-Host "Ignoring out-of-range: $($bad -join ', ')" -ForegroundColor Yellow }
    return @($nums | Where-Object { $_ -ge 1 -and $_ -le 69 })
}
function Show-List($skulls, $found, [switch]$ShowFound) {
    $areas = @($skulls | ForEach-Object { $_.A } | Select-Object -Unique)   # keeps route order
    foreach ($area in $areas) {
        $all = @($Skulls | Where-Object { $_.A -eq $area })
        $have = @($all | Where-Object { $found -contains $_.N }).Count
        Write-Host ""
        Write-Host ("== {0}  ({1}/{2})" -f $area, $have, $all.Count) -ForegroundColor Cyan
        foreach ($s in @($skulls | Where-Object { $_.A -eq $area })) {
            $got = $found -contains $s.N
            if ($got -and -not $ShowFound) { continue }
            $mark = if ($got) { '[x]' } else { '[ ]' }
            $color = if ($got) { 'DarkGray' } else { 'White' }
            Write-Host ("  {0} #{1,-2} {2}" -f $mark, $s.N, $s.T) -ForegroundColor $color
            if (-not $got) {
                Write-Host ("        {0}" -f $s.H) -ForegroundColor Gray
                if ($s.R) { Write-Host ("        Needs: {0}" -f $s.R) -ForegroundColor DarkYellow }
            }
        }
    }
}
function Show-Summary($found) {
    $n = $found.Count
    Write-Host ""
    Write-Host ("Collected {0}/69 - missing {1}" -f $n, (69 - $n)) -ForegroundColor Green
    $next = @(10, 30, 69) | Where-Object { $_ -gt $n } | Select-Object -First 1
    if ($next) { Write-Host ("Next hand-in milestone: {0} (turn skulls in at the door under the Petrified Garden)" -f $next) }
}

$found = Load-Found

switch ($Command.ToLower()) {
    'found' {
        $nums = Parse-Numbers $Args2
        $found = @($found + $nums)
        Save-Found $found
        $found = Load-Found
        foreach ($n in $nums) { $s = $Skulls | Where-Object { $_.N -eq $n }; Write-Host "Marked #$n ($($s.A): $($s.T))" -ForegroundColor Green }
        Show-Summary $found
    }
    'unfound' {
        $nums = Parse-Numbers $Args2
        $found = @($found | Where-Object { $nums -notcontains $_ })
        Save-Found $found
        Write-Host "Un-marked: $($nums -join ', ')"
        Show-Summary $found
    }
    'area' {
        $q = ($Args2 -join ' ')
        $hits = @($Skulls | Where-Object { $_.A -like "*$q*" })
        if (-not $hits) { Write-Host "No area matches '$q'. Areas: $((($Skulls | ForEach-Object { $_.A }) | Select-Object -Unique) -join ', ')"; break }
        Show-List $hits $found -ShowFound
    }
    'all'   { Show-List $Skulls $found -ShowFound; Show-Summary $found }
    'reset' { Save-Found @(); Write-Host 'Progress cleared.' }
    default {
        $missing = @($Skulls | Where-Object { $found -notcontains $_.N })
        if (-not $missing) { Write-Host 'All 69 collected! Go do the ritual for The Call From Beyond / Ending 4.' -ForegroundColor Green }
        else { Show-List $missing $found }
        Show-Summary $found
    }
}
