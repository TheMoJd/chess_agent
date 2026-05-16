import { ChangeDetectionStrategy, Component } from '@angular/core';
import { BoardComponent } from './components/board/board.component';
import { BoardControlsComponent } from './components/board-controls/board-controls.component';
import { ChatPanelComponent } from './components/chat-panel/chat-panel.component';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [BoardComponent, BoardControlsComponent, ChatPanelComponent],
  templateUrl: './app.html',
  styleUrl: './app.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class App {}
