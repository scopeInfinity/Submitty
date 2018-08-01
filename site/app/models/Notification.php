<?php

namespace app\models;

use app\libraries\Core;

/**
 * Class Notification
 *
 * @method void     setViewOnly($view_only)
 * @method void     setId($id)
 * @method void     setComponent($component)
 * @method void     setSeen($isSeen)
 * @method void     setElapsedTime($duration)
 * @method void     setCreatedAt($time)
 * @method void     setNotifyMetadata()
 * @method void     setNotifyContent()
 *
 * @method bool     isViewOnly()
 * @method int      getId()
 * @method string   getComponent()
 * @method bool     isSeen()
 * @method real     getElapsedTime()
 * @method string   getCreatedAt()
 * @method string   getCurrentUser()
 *
 * @method string   getNotifySource()
 * @method string   getNotifyTarget()
 * @method string   getNotifyContent()
 * @method string   getNotifyMetadata()
 * @method bool     getNotifyNotToSource()
 */
class Notification extends AbstractModel {
    /** @property @var bool Notification fetched from DB */
    protected $view_only;

    /** @property @var string Type of notification */
    protected $component;
    /** @property @var string Current logged in user */
    protected $current_user;

    /** @property @var string Notification source user (can be null) */
    protected $notify_source;
    /** @property @var string Notification target user(s) (null implies all users) */
    protected $notify_target;
    /** @property @var string Notification text content */
    protected $notify_content;
    /** @property @var string Notification information about redirection link */
    protected $notify_metadata;
    /** @property @var bool Should $notify_source be ignored from $notify_target */
    protected $notify_not_to_source;

    /** @property @var int Notification ID */
    protected $id;
    /** @property @var bool Is notification already seen */
    protected $seen;
    /** @property @var real Time elapsed from creation of notification in secs */
    protected $elapsed_time;
    /** @property @var string Timestamp for creation of notification */
    protected $created_at;


    /**
     * Notifications constructor.
     *
     * @param Core  $core
     * @param array $details
     */
    public function __construct(Core $core, $details=array()) {
        parent::__construct($core);
        if (count($details) == 0) {
            return;
        }
        if(!empty($details['view_only'])){
            $this->setViewOnly(true);
            $this->setId($details['id']);
            $this->setSeen($details['seen']);
            $this->setComponent($details['component']);
            $this->setElapsedTime($details['elapsed_time']);
            $this->setCreatedAt($details['created_at']);
            $this->setNotifyMetadata($details['metadata']);
            $this->setNotifyContent($details['content']);
        } else {
            $this->setViewOnly(false);
            $this->setNotifyNotToSource(true);
            $this->setCurrentUser($this->core->getUser()->getId());
            $this->setComponent($details['component']);
            switch ($this->getComponent()) {
                case 'forum':
                    $this->handleForum($details);
                    break;
                default:
                    // Prevent notification to be pushed in database
                    $this->setComponent("invalid");
                    break;
            }
        }
    }

    /**
     * Handles notifications related to forum
     *
     * @param array $details
     */
    private function handleForum($details) {
        switch ($details['type']) {
            case 'new_announcement':
                $this->setNotifyMetadata(json_encode(array('component' => 'forum', 'page' => 'view_thread', 'thread_id' => $details['thread_id'])));
                $this->setNotifyContent("New Announcement: ".$details['thread_title']);
                $this->setNotifySource($this->getCurrentUser());
                $this->setNotifyTarget(null);
                break;
            case 'updated_announcement':
                $this->setNotifyMetadata(json_encode(array('component' => 'forum', 'page' => 'view_thread', 'thread_id' => $details['thread_id'])));
                $this->setNotifyContent("Announcement: ".$details['thread_title']);
                $this->setNotifySource($this->getCurrentUser());
                $this->setNotifyTarget(null);
                break;
            case 'reply':
                // TODO: Redirect to post itself
                $this->setNotifyMetadata(json_encode(array('component' => 'forum', 'page' => 'view_thread', 'thread_id' => $details['thread_id'])));
                $this->setNotifyContent("Reply: Your post '".$this->textShortner($details['post_content'])."' got new a reply from ".$this->getCurrentUser());
                $this->setNotifySource($this->getCurrentUser());
                $this->setNotifyTarget($details['reply_to']);
                break;
            case 'merge_thread':
                // TODO: Redirect to post itself
                $this->setNotifyMetadata(json_encode(array('component' => 'forum', 'page' => 'view_thread', 'thread_id' => $details['parent_thread_id'])));
                $this->setNotifyContent("Thread Merged: '".$this->textShortner($details['child_thread_title'])."' got merged into '".$this->textShortner($details['parent_thread_title'])."'");
                $this->setNotifySource($this->getCurrentUser());
                $this->setNotifyTarget($details['reply_to']);
                break;
            case 'edited':
                // TODO: Redirect to post itself(if exists)
                $this->setNotifyMetadata(json_encode(array('component' => 'forum', 'page' => 'view_thread', 'thread_id' => $details['thread_id'])));
                $this->setNotifyContent("Update: Your thread/post '".$this->textShortner($details['post_content'])."' got an edit from ".$this->getCurrentUser());
                $this->setNotifySource($this->getCurrentUser());
                $this->setNotifyTarget($details['reply_to']);
                break;
            case 'deleted':
                $this->setNotifyMetadata(json_encode(array('component' => 'forum', 'page' => 'view_thread', 'thread_id' => $details['thread_id'])));
                $this->setNotifyContent("Deleted: Your thread/post '".$this->textShortner($details['post_content'])."' was deleted by ".$this->getCurrentUser());
                $this->setNotifySource($this->getCurrentUser());
                $this->setNotifyTarget($details['reply_to']);
                break;
            case 'undeleted':
                // TODO: Redirect to post itself(if exists)
                $this->setNotifyMetadata(json_encode(array('component' => 'forum', 'page' => 'view_thread', 'thread_id' => $details['thread_id'])));
                $this->setNotifyContent("Undeleted: Your thread/post '".$this->textShortner($details['post_content'])."' has been undeleted by ".$this->getCurrentUser());
                $this->setNotifySource($this->getCurrentUser());
                $this->setNotifyTarget($details['reply_to']);
                break;
            default:
                return;
        }
    }

    /**
     * Trim long $message upto 40 character and filter newline
     *
     * @param string $message
     * @return $trimmed_message
     */
    private function textShortner($message) {
        return mb_strimwidth(str_replace("\n", " ", $message), 0, 40, "...");
    }

    /**
     * Returns relative time if time is in last 24 hours
     * else returns absolute time
     *
     * @return string $formatted_time
     */
    public function getNotifyTime() {
        $elapsed_time = $this->getElapsedTime();
        $actual_time = $this->getCreatedAt();
        if($elapsed_time < 60){
            return "Less than a minute ago";
        } else if($elapsed_time < 3600){
            $minutes = floor($elapsed_time/60);
            if($minutes == 1)
                return "1 minute ago";
            else
                return "{$minutes} minutes ago";
        } else if($elapsed_time < 3600*24){
            $hours = floor($elapsed_time/3600);
            if($hours == 1)
                return "1 hour ago";
            else
                return "{$hours} hours ago";
        } else {
            return date_format(date_create($actual_time), "n/j g:i A");
        }
    }
}
